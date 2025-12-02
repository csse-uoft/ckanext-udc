import subprocess
import ckan.authz as authz
from ckan.types import Context
import ckan.logic as logic
from ckan.types import Context
from ckan.common import _


def reload_supervisord(context: Context, data: dict) -> str:
    # Check admin
    if not authz.is_sysadmin(context.get("user")):
        raise logic.NotAuthorized(_("You are not authorized to view this page"))

    task = data.get("task")
    if task == "ckan":
        target = "ckan-uwsgi:"
    elif task == "worker":
        target = "ckan-worker:"
    elif task == "all":
        target = "all"
    else:
        raise logic.ValidationError(_("task must be one of 'ckan', 'worker', or 'all'"))

    try:
        subprocess.run(["sudo", "supervisorctl", "restart", target], check=True)
    except subprocess.CalledProcessError as e:
        return {"success": False, "error": str(e)}

    return {"success": True}


@logic.side_effect_free
def get_system_stats(context: Context, data: dict) -> dict:
    """
    Remember to add `www-data ALL=(ALL) NOPASSWD: /usr/bin/supervisorctl` to the sudoers file.
    via `sudo visudo`
    """
    # Check admin
    if not authz.is_sysadmin(context.get("user")):
        raise logic.NotAuthorized("You are not authorized to view this page")

    # Get CPU, memory, and disk usage
    cpu_usage = subprocess.run(["top", "-bn1"], stdout=subprocess.PIPE).stdout.decode()
    memory_usage = subprocess.run(
        ["free", "-h"], stdout=subprocess.PIPE
    ).stdout.decode()
    disk_usage = subprocess.run(["df", "-h"], stdout=subprocess.PIPE).stdout.decode()

    return {
        "cpu_usage": cpu_usage,
        "memory_usage": memory_usage,
        "disk_usage": disk_usage,
    }
