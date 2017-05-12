# jld-fileserver

This is an NFS server, based on the gcr.io "volume-nfs" server.  I
honestly don't quite understand what's going on here, but: apparently
you need one of these to serve up a PersistentVolume as NFS, but the
defined-and-exported volume (from the NFS server deployment) isn't what
gets exported, an autocreated volume from GKE is.

In any event, what you want to do is define a minimal-size volume that
the NFS server mounts and exports, and then create your PersistentVolume
and PersistentVolumeClaim as if the NFS server was exporting those.

Then, somehow, everything works.  Yeah, I know.  Beats me too.
