import ipywidgets as widgets
from ipywidgets import Button, HBox, VBox, Layout
from IPython.display import display, clear_output


def catchInterrupt(func):
    """decorator : when interupt occurs the display is lost if you don't catch it
       TODO * <view>.stop_data_fetch()  # stop

    ."""

    def catch_interrupt(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except (KeyboardInterrupt):
            pass

    return catch_interrupt


def display_view_stop(eventView, period=2):
    """Wrapper for streamsx.rest_primitives.View.display() to have button. """
    button = widgets.Button(description="Stop Updating")
    display(button)
    eventView.display(period=period)

    def on_button_clicked(b):
        eventView.stop_data_fetch()
        b.description = "Stopped"

    button.on_click(on_button_clicked)


def view_events(views):
    """
    Build interface to display a list of views and
    display view when selected from list.

    """
    view_names = [view.name for view in views]
    nameView = dict(zip(view_names, views))
    select = widgets.RadioButtons(
        options=view_names,
        value=None,
        description="Select view to display",
        disabled=False,
    )

    def on_change(b):
        if b["name"] == "label":
            clear_output(wait=True)
            [view.stop_data_fetch() for view in views]
            display(select)
            display_view_stop(nameView[b["new"]], period=2)

    select.observe(on_change)
    display(select)


def find_job(instance, job_name=None):
    """locate job within instance"""
    for job in instance.get_jobs():
        if job.applicationName.split("::")[-1] == job_name:
            return job
    else:
        return None


def get_view(instance, job_name=None, view_name="view"):
    job = find_job(instance, job_name)
    return job.get_views(view_name)


def display_views(instance, job_name):
    "Locate/promote and display all views of a job"
    job = find_job(instance, job_name=job_name)
    if job is None:
        print("Failed to locate job")
    else:
        views = job.get_views()
        view_events(views)


def list_jobs(_instance=None, cancel=False):
    """
    Interactive selection of jobs to cancel.

    Prompts with SelectMultiple widget, if thier are no jobs, your presente with a blank list.

    """
    active_jobs = {
        "{}:{}".format(job.name, job.health): job for job in _instance.get_jobs()
    }

    selectMultiple_jobs = widgets.SelectMultiple(
        options=active_jobs.keys(),
        value=[],
        rows=len(active_jobs),
        description="Cancel jobs(s)" if cancel else "Active job(s):",
        layout=Layout(width="60%"),
    )
    cancel_jobs = widgets.ToggleButton(
        value=False,
        description="Cancel",
        disabled=False,
        button_style="warning",  # 'success', 'info', 'warning', 'danger' or ''
        tooltip="Delete selected jobs",
        icon="stop",
    )

    def on_value_change(change):
        for job in selectMultiple_jobs.value:
            print("canceling job:", job, active_jobs[job].cancel())
        cancel_jobs.disabled = True
        selectMultiple_jobs.disabled = True

    cancel_jobs.observe(on_value_change, names="value")
    if cancel:
        return HBox([selectMultiple_jobs, cancel_jobs])
    else:
        return HBox([selectMultiple_jobs])


from streamsx.topology import context
# import streamsx.rest as rest
from streamsx.rest_primitives import Instance



def submitToStreams(topology, streams_cfg):
    # Create local copy of the streams config so this can be thread-safe
    local_streams_cfg = dict(streams_cfg)
    streams_instance = Instance.of_service(local_streams_cfg)

    # Cancel the job from the instance if it is already running...
    for job in streams_instance.get_jobs():
        if job.name == topology.name:
            print("Cancelling old job:", job.name)
            job.cancel()

    # Set the job config
    job_config = context.JobConfig(job_name=topology.name, tracing="debug")
    job_config.add(local_streams_cfg)

    # Actually submit the job
    print("Building and submitting new job:", topology.name)
    submission_result = context.submit("DISTRIBUTED", topology, local_streams_cfg)
    return submission_result
