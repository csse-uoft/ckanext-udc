import socketio
from ckan.plugins.toolkit import config


class SocketClient:
    namespace = "/import-worker"
    executor = None
    registered = False
    stop_requested = False

    def __init__(self, job_id: str):
        """
        Initializes the Socket.IO client and connects to the given URL.

        :param job_id: The job ID to register with the server.
        :param worker_idx: The worker index to register with the server.
        """
        self.sio = socketio.Client(logger=True)
        self.registered = False  # Flag to track if the client is registered

        # Event listener for 'registered' event from the server
        @self.sio.on("registered", namespace=self.namespace)
        def on_registered():
            self.registered = True
            print("Client registered successfully with the server.")

        self.sio.connect(
            "ws://localhost:5000", transports=["websocket"], namespaces=[self.namespace]
        )
        # Reuse beaker.session.validate_key for socket validation 
        valication_key = config.get("beaker.session.validate_key")
        self.sio.emit("register", data=(job_id, valication_key), namespace=self.namespace)
        
        @self.sio.on("stop_job", namespace=self.namespace)
        def on_stop_requested():
            # Ask the executor to stop the job gracefully
            print("stop_job requested")
            self.stop_requested = True
            if self.executor:
                print("Shutting down executor")
                self.executor.shutdown(cancel_futures=True)
                self.sio.emit("job_stopped", (job_id,), namespace=self.namespace)
            

    def send_message(self, log_level: str, message: str):
        """
        Send a message with the specified log level to the server.

        :param log_level: The level of the log (e.g., 'info', 'error', 'debug', 'exception').
        :param message: The message content to send.
        """
        if self.registered:
            data = {"log_level": log_level, "message": message}
            self.sio.emit("log_message", data, namespace=self.namespace)
        else:
            print("Client is not registered yet. Message not sent.")

    def update_progress(self, current: int, total: int):
        """
        Sends the current progress to the server.

        :param current: The current progress value.
        :param total: The total value for progress completion.
        """
        if self.registered:
            progress_data = {"current": current, "total": total}
            self.sio.emit("progress_update", progress_data, namespace=self.namespace)
        else:
            print("Client is not registered yet. Progress not sent.")
    
    def finish_one(self, type: str, data: dict):
        """
        Sends a message to the server indicating that a package import has been completed.
        
        type: created, updated, deleted, errored
        data: {
            "id": id, "name": name, "title": title, 
            "logs": [str],
            "duplications": {"id": id, "name": name, "title": title}
            }
        """
        if self.registered:
            progress_data = {"type": type, "data": data}
            self.sio.emit("finish_one", progress_data, namespace=self.namespace)
        else:
            print("Client is not registered yet. Progress not sent.")

    def disconnect(self):
        """
        Disconnects the client from the server.
        """
        self.sio.disconnect()


# Example usage
# client = SocketClient('job123', 1)
# client.send_message('info', 'Client initialized and ready.')  # This will wait until registered
# client.update_progress(50, 100)
# client.disconnect()
