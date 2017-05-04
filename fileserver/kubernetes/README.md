# File Server for Jupyterlab Demo

Currently we're using NFS.  At some point we probably want to use Ceph
instead.

# Order of Operations

This is anything but obvious.  I have done it working from the steps at
https://github.com/kubernetes/kubernetes/tree/master/examples/volumes/nfs
with some minor modifications.

## StorageClass

Create the StorageClass resource first, which will give you access to
SSD volumes:

`kubectl create -f jld-fileserver-storageclass.yml`

(the `pd-ssd` type parameter is what does that for you)

## Physical Storage PersistentVolumeClaim

Next, you create a PersistentVolumeClaim (*not* a PersistentVolume!) for
the underlying storage:

`kubectl create -f jld-fileserver-physpvc.yml`

This will automagically create a PersistentVolume to back it.  Yeah, I
wouldn't have figured that out on my own either.

## NFS Server

The next step is to create an NFS Server that serves up the actual
disk.

`kubectl create -f jld-fileserver-deployment.yml`

I created my own NFS Server image, basing it on the stuff found inside
the gcr.io "volume-nfs" server.  You could probably just use Google's
image and it'd be fine.

## Service

Create a service to expose the NFS server (only inside the cluster)
with the following:

`kubectl create -f jld-fileserver-service.yml`

## NFS Persistent Volume

This one is where it all goes pear-shaped.

Here comes the first really maddening thing: PersistentVolumes are not
namespaced.

And here's the second one: the NFS server defined here has to be an IP
address, not a name.

And here's the third one: you need to specify local locking in the PV
options or else the notebook will simply get stuck in disk wait when it
runs.  This does mean that you really shouldn't run two pods as the same
user at the same time, certainly not pointing to the same notebook.

Those two things combine to make it tough to do a truly automated
deployment of a new Jupyterlab Demo instance, because you have to create
the service, then pull the IP address off it and use that in the PV
definition.

So what you should do is to copy the template to a file you're going to 
work from: `cp jld-fileserver-pv.yml.template workingpv.yml`.  Then edit
the working copy.  Replace the `{{FIXME}}` in the name with something
indicating the namespace, and replace the `{{FIXME}}` in the server
field with the IP address of the service you created in the previous
step.

Then create the resource: `kubectl create -f workingpv.yml`

## NFS Mount PersistentVolumeClaim

From here on it's smooth sailing.  Create a PersistentVolumeClaim
referring to the PersistentVolume you just created:

`kubectl create -f jld-fileserver-pvc.yml`

Now you're done!

