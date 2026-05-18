# SMB Protocol Connection Reference

## Connection Lifecycle

```python
import uuid
from smbprotocol.connection import Connection, Dialects
from smbprotocol.session import Session
from smbprotocol.tree import TreeConnect
from smbprotocol.open import Open, FilePipePrinterAccessMask, ImpersonationLevel

# 1. Connect
conn = Connection(uuid.uuid4(), host, 445)
conn.connect(Dialects.SMB_3_1_1)

# 2. Authenticate
sess = Session(conn, username, password)
sess.connect()

# 3. Connect to a share
tree = TreeConnect(sess, r"\\host\share")
tree.connect()

# 4. Open a file/directory
o = Open(sess, tree, r"\path\to\folder_or_file")
o.create(
    FilePipePrinterAccessMask.FILE_LIST_DIRECTORY,  # FILE_READ_DATA for files
    file_attributes=0,
    share_access=0x7,  # FILE_SHARE_READ | WRITE | DELETE
    create_disposition=1,  # FILE_OPEN
    impersonation_level=ImpersonationLevel.Impersonation,
)

# 5. List or read
files = o.query_directory("*")  # directories
data = o.read(0, 65536)          # files

# 6. Clean up
o.close()
tree.disconnect()
conn.disconnect()
```

## Key Access Masks

| Operation | Access Mask |
|---|---|
| List directory | `FilePipePrinterAccessMask.FILE_LIST_DIRECTORY` |
| Read file | `FilePipePrinterAccessMask.FILE_READ_DATA` |
| Write file | `FilePipePrinterAccessMask.FILE_WRITE_DATA` |
| Create file | `FilePipePrinterAccessMask.FILE_ADD_FILE` |

## Common Share Paths

| Share | Windows Path | Requires Admin |
|---|---|---|
| C$ | \Users\... | Yes |
| ADMIN$ | C:\Windows | Yes |
| IPC$ | (RPC pipe) | No |
| Users | C:\Users | No, but share must be created |

## Error Handling

| Error | Meaning |
|---|---|
| STATUS_ACCESS_DENIED (0xc0000022) | User auth OK but lacks permissions on share/folder |
| STATUS_LOGON_FAILURE | Wrong password |
| STATUS_BAD_NETWORK_NAME | Share does not exist |
| STATUS_OBJECT_NAME_NOT_FOUND | Folder/file path doesn't exist |

## TTL-based OS Detection

- TTL=128 → Windows (default)
- TTL=64 → Linux/Unix
- TTL=255 → Network device/Cisco

## Port Service Map

| Port | Service | Protocol |
|---|---|---|
| 22 | SSH | TCP |
| 445 | SMB/CIFS | TCP |
| 135 | RPC/DCOM | TCP |
| 3389 | RDP | TCP |
| 5985 | WinRM (HTTP) | TCP |
| 5986 | WinRM (HTTPS) | TCP |
