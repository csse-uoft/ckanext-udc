from ckanext.udc_import_other_portals.model import CUDCImportJob, CUDCImportConfig
from ckan.plugins.toolkit import config
from flask import request, session
from flask_socketio import (
    SocketIO,
    emit,
    disconnect as sio_disconnect,
    join_room,
    leave_room,
)
import logging
from pprint import pprint
from ckan.lib.api_token import decode
from ckan.model import User
from ckan.authz import is_sysadmin
from ckan import model

# from ckan.common import current_user


log = logging.getLogger(__name__)


def initSocketIO(app):
    socketio = SocketIO(app, debug=False, logger=False, manage_session=True)
    worker_data = (
        {}
    )  # Structure: { job_id: { 'sid': sid, 'logs': [], 'progress': None, 'finished': [] } }
    client_map = {}  # Structure: { sid: job_id }
    

    @socketio.event(namespace="/admin-dashboard")
    def connect(auth):
        # Notes: flask beaker session does not work with socketIO for unknown reason.
        # Using alternative way to authenticate users.
        if not auth or not auth.get("token"):
            log.info("Dropped ws connection without token.")
            emit("error", {"message": "token not provided"})
            sio_disconnect()
            return
        data = decode(auth["token"])
        user_id = data["user_id"]
        if not is_sysadmin(user_id):
            emit("error", {"message": "user not admin"})
            sio_disconnect()

    @socketio.event(namespace="/admin-dashboard")
    def get_running_jobs(config_id: str):
        jobs = CUDCImportJob.get_running_jobs_by_config_id(config_id)
        emit("running_jobs", {job.id: job.as_dict() for job in jobs})

    @socketio.event(namespace="/admin-dashboard")
    def stop_job(job_id: str):
        if not worker_data.get(job_id):
            job = CUDCImportJob.get(job_id)
            config_id = job.import_config_id
            job.is_running = False
            model.Session.add(job)
            model.Session.commit()
            jobs = CUDCImportJob.get_running_jobs_by_config_id(config_id)
            if not jobs:
                import_config = CUDCImportConfig.get(config_id)
                import_config.is_running = False
                model.Session.add(import_config)
                model.Session.commit()
            
        else:
            emit("stop_job", room=job_id, namespace="/import-worker")
    
    
    @socketio.event(namespace="/import-worker")
    def job_stopped(job_id):
        """Forward the job_stopped event to the admin dashboard."""
        
        sid = request.sid
        log.info(f"Received job_stopped from sid {sid}")

        # Check if the client is registered
        if sid not in client_map:
            log.error(
                f"Received job_stopped from unregistered client {sid}. Ignoring message."
            )
            return
        
        emit(
            "job_stopped", (job_id), broadcast=True, namespace="/admin-dashboard"
        )
         

    @socketio.event(namespace="/admin-dashboard")
    def subscribe(import_id):
        """
        Handles subscription from the admin dashboard to a specific job_id.

        :param import_id: The ID of the import/job to subscribe to.
        """
        sid = request.sid
        join_room(import_id)  # Join a room named after the job_id

        if import_id in worker_data:
            # Emit the entire log and progress history for the job_id to the newly subscribed client
            for log_entry in worker_data[import_id].get("logs", []):
                emit("log_message", log_entry, room=sid, namespace="/admin-dashboard")
            if worker_data[import_id].get("progress") is not None:
                emit(
                    "progress_update",
                    worker_data[import_id]["progress"],
                    room=sid,
                    namespace="/admin-dashboard",
                )

        emit("subscribed", {"job_id": import_id})
        log.info(f"Admin client {sid} subscribed to job_id {import_id}")

    @socketio.event(namespace="/admin-dashboard")
    def unsubscribe(import_id):
        """
        Handles unsubscription from a specific job_id.

        :param import_id: The ID of the import/job to unsubscribe from.
        """
        sid = request.sid
        leave_room(import_id)  # Leave the room named after the job_id
        emit("unsubscribed", {"job_id": import_id})
        log.info(f"Admin client {sid} unsubscribed from job_id {import_id}")

    @socketio.event(namespace="/admin-dashboard")
    def get_job_status(import_id):
        """
        Allows the frontend to request the current status of a specific job_id.

        :param import_id: The ID of the import/job.
        """
        if import_id in worker_data:
            emit("job_status", worker_data[import_id])
            log.info(
                f"Sent status for job_id {import_id} to admin client {request.sid}"
            )
        else:
            emit("job_status", {"error": f"Job ID {import_id} not found."})
            log.error(
                f"Admin client {request.sid} requested status for nonexistent job_id {import_id}"
            )

    @socketio.event(namespace="/import-worker")
    def register(job_id: str, valication_key: str):
        """
        Registers a worker with the given job_id.

        :param job_id: The ID of the job to register.
        """
        sid = request.sid  # Get the unique session ID for the client
        log.info(f"Register event received from sid {sid}: job_id={job_id}")

        if config.get("beaker.session.validate_key") != valication_key:
            emit(
                "error",
                {"message": f"Invalid valication_key {valication_key} provided."},
            )
            sio_disconnect()
            return

        # Verify if the job_id exists in the database
        job = CUDCImportJob.get(job_id)
        if not job:
            log.error(f"Job ID {job_id} not found. Disconnecting client {sid}.")
            emit("error", {"message": f"Job ID {job_id} not found."})
            sio_disconnect()
            return

        # Initialize job entry if it doesn't exist
        if job_id not in worker_data:
            worker_data[job_id] = {
                "sid": sid,
                "logs": [],  # Store logs for this worker
                "progress": None,  # Store the latest progress for this worker
                "finished": [],  # Store the finished packages
            }

        # Map the client's sid to their job_id
        client_map[sid] = job_id
        
        join_room(job_id)
        
        # Emit confirmation back to the client
        emit("registered")
        
        emit(
            "job_started", (job.as_dict()), broadcast=True, namespace="/admin-dashboard"
        )
        log.info(f"Worker registered for job {job_id} with sid {sid}.")

    @socketio.event(namespace="/import-worker")
    def log_message(data):
        """
        Handles log messages sent by workers.

        :param data: Dictionary containing 'log_level' and 'message'.
        """
        sid = request.sid
        # log.info(f"Received log_message from sid {sid}: {data}")

        # Check if the client is registered
        if sid not in client_map:
            log.error(
                f"Received log_message from unregistered client {sid}. Ignoring message."
            )
            return

        job_id = client_map[sid]

        log_level = data.get("log_level")
        message = data.get("message")

        if not log_level or not message:
            log.error(f"Invalid log_message data from client {sid}: {data}")
            return

        log_entry = {"log_level": log_level, "message": message}

        # Save the log entry in worker_data
        worker_data[job_id]["logs"].append(log_entry)

        # Emit the log message to the admin-dashboard room corresponding to the job_id
        emit("log_message", log_entry, room=job_id, namespace="/admin-dashboard")

        # Log the message to the server logs
        log_msg = f"Job {job_id}: {message}"
        if log_level == "info":
            log.info(log_msg)
        elif log_level == "error":
            log.error(log_msg)
        elif log_level == "debug":
            log.debug(log_msg)
        elif log_level == "exception":
            log.exception(log_msg)
        else:
            log.warning(f"Unknown log level '{log_level}' from client {sid}: {message}")

    @socketio.event(namespace="/import-worker")
    def progress_update(data):
        """
        Handles progress updates sent by workers.

        :param data: Dictionary containing 'current' and 'total'.
        """
        sid = request.sid
        # log.info(f"Received progress_update from sid {sid}: {data}")

        # Check if the client is registered
        if sid not in client_map:
            log.error(
                f"Received progress_update from unregistered client {sid}. Ignoring update."
            )
            return

        job_id = client_map[sid]

        current = data.get("current")
        total = data.get("total")

        if current is None or total is None:
            log.error(f"Invalid progress_update data from client {sid}: {data}")
            return

        progress_entry = {"current": current, "total": total}

        # Save the progress update in worker_data
        worker_data[job_id]["progress"] = progress_entry

        # Emit the progress update to the admin-dashboard room corresponding to the job_id
        emit(
            "progress_update", progress_entry, room=job_id, namespace="/admin-dashboard"
        )

        # Log the progress update to the server logs
        progress = f"Progress for job {job_id}: {current}/{total}"
        log.info(progress)
        
    @socketio.event(namespace="/import-worker")
    def finish_one(data):
        """
        Handle the finish_one event sent by the worker client.
        
        data: {
            "type": "created" | "updated" | "deleted" | "errored",
            "data": {
                "id": id, "name": name, "title": title, 
                "logs": [str],
                "duplications": {"id": id, "name": name, "title": title}
            }
        }
        """
        print("Import job finished:", data)
        sid = request.sid
        # log.info(f"Received progress_update from sid {sid}: {data}")

        # Check if the client is registered
        if sid not in client_map:
            log.error(
                f"Received progress_update from unregistered client {sid}. Ignoring update."
            )
            return

        job_id = client_map[sid]
        
        # Save the progress update in worker_data
        worker_data[job_id]["finished"].append(data)

        # Emit the progress update to the admin-dashboard room corresponding to the job_id
        emit(
            "finish_one", data, room=job_id, namespace="/admin-dashboard"
        )
        
        

    @socketio.event(namespace="/import-worker")
    def disconnect_request():
        """
        Handles explicit disconnect requests from clients.
        """
        log.info(f"Client {request.sid} requested disconnect.")
        sio_disconnect()

    @socketio.event(namespace="/import-worker")
    def disconnect():
        """
        Handles client disconnections.
        """
        sid = request.sid
        log.info(f"Client {sid} disconnected.")

        if sid in client_map:
            job_id = client_map.pop(sid)
            leave_room(job_id)
            if job_id in worker_data:
                # Store finished data in the database
                job = CUDCImportJob.get(job_id)
                job.other_data = {'finished': worker_data[job_id]["finished"]}
                model.Session.add(job)
                model.Session.commit()
                
                del worker_data[job_id]
                log.info(f"Removed worker data for job {job_id} upon disconnect.")
        
        emit(
            "job_stopped", (job_id), broadcast=True, namespace="/admin-dashboard"
        )

    log.info("Socket.io server initialized and ready.")

    return socketio
