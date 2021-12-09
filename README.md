# ilandinfo

ilandinfo is a tool to help extract information from the iland Cloud
REST API.

## Quick start

ilandinfo was built and tested with Python version 3.9.

ilandinfo requires:

* [iland-sdk](https://github.com/ilanddev/python-sdk)
* [python-dateutil](https://pypi.org/project/python-dateutil/)

Here's the recommended installation process to get up and working quickly:

1. In the iland Secure Cloud Console, create a new user.
2. Assign the **Read-Only API User** role to this new user.
3. Create a virtual environment.
4. Install the iland-sdk.
5. Edit the **creds.json** file with your iland Cloud API credentials. Use *example.creds.json* as a template.
6. Run `ilandinfo.py -h` for help.

```shell
$ python3 -m venv iland

$ source iland/bin/activate

(iland) $ pip install iland-sdk python-dateutil

(iland) $ ./ilandinfo.py inventory company
Name, UUID
bestCompanyNameEver, 123456789
```
