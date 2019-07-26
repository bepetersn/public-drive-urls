# public-drive-urls

Use this module to turn a Google Drive-provided
share url for a public file into a url pointing to
the actual resource. Raises exceptions if the URL
either doesn't resolve, or appears to point to a
file that isn't publicly accessible, and watching 
for the latter is actually the primary use case.

This module provides for your use a class, `DriveResource`. 
DriveResources represent resources hosted at docs.google.com
or drive.google.com, and how they can be accessed (assuming
they are publicly accessible).
Typically, a user might share their document online using
a certain URL available from the web UI at these sites
by an action called sharing (sending a "share url"). While
the share url is all you need to access these resources if
you are using a browser, it isn't very helpful if you need
to download the resource directly, e.g. from a script --
HTML, javascript and CSS will all get in the way.
This class allows you to go from a share url to the url
needed to download your document ("access url").
Code like the following exemplifies this class's intended usage:
```
from public_drive_urls import DriveResource
r = DriveResource.from_share_url('http://drive.google.com/file/d/foo/')
access_url = r.get_access_url()
# print the documents contents
requests.get(access_url).content
```
Alternatively, if you knew the DriveResource's hosting
type and id (by doing your own parsing, etc), you could
instantiate this class more directly as follows:
```
r = DriveResource(id='foo', hosting_type='file')
access_url = r.get_access_url()
```
