# jupyterlabdemo

## Running

* `docker run -it --rm -p 8000:8000 --name jupyterlabdemo
  lsstsqre/jupyterlabdemo`
   
* Go to `http://localhost:8000` and log in as `jupyterlab`, any password
  or none (obviously this is not going to stick around to production).

## Building

* `docker build -t lsstsqre/jupyterlabdemo .`
