# jupyterlabdemo

## Running

* `docker run -it --rm -p 8000:8000 --name jupyterlabdemo
  lsstsqre/jupyterlabdemo`
   
* Go to `http://localhost:8000` and log in as `jupyterlab`, any password
  or none (obviously this is not going to stick around to production).

## Building

* `docker build -t lsstsqre/jupyterlabdemo .`

## Help!

I don't get why this isn't working.  I am using the same configs with
Conda as I am with virtualenv.  In the venv case it's a user-specific
virtualenv, and in the conda case it's system-wide, but it doesn't seem
to matter--I get the same result when I install a conda environment as
the `jupyterlab` user.

`docker run -it -p 8000:8000 --rm lsstsqre/jupyterlabdemo /bin/bash --login`

If you then `./run-jupyterhub.bash` everything starts fine.  But if you
then hit `http://localhost:8000` and log in as `jupyterlab`, you just
get a blank screen.  Nothing in the config seems to show an error.

If you kill that with Ctrl-C, you can start jupyterlab directly:

`jupyter-lab --debug --ip=* --port=8000 --notebook-dir=data`

Hit that using the URL that is the last line of the startup message: it
works fine; both Python 2 and Python 3 work.

So what I am failing to understand, and what I don't see any logs to
chase to get to an understanding, is why the hub-launching-lab linkage
fails here, when it works fine in a venv environment, using the same
configs (use the `master` branch to see that).

Ideas would be appreciated.

