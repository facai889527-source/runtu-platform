"""Local server key material: no browser export; restrictive OS ACL before writing."""
import os
from pathlib import Path
import subprocess
from cryptography.fernet import Fernet
from pydantic import SecretStr

class PrivateKeyError(Exception):pass

class PrivateKeyStore:
    def __init__(self,path):self.path=Path(path);self.cache=None

    def access(self,path,protect=False):
        if path.is_symlink():raise PrivateKeyError()
        if os.name!='nt':
            if protect:os.chmod(path,0o700 if path.is_dir() else 0o600)
            if path.stat().st_mode & 0o077:raise PrivateKeyError()
            return
        # Constant script; only a non-secret server-selected path is passed via
        # environment. Neither key values nor process/ACL diagnostics are logged.
        script=r"""$ErrorActionPreference='Stop'
$p=$env:RUNTU_PRIVATE_KEY_TARGET
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User
$sys=[Security.Principal.SecurityIdentifier]::new('S-1-5-18')
$a=Get-Acl -LiteralPath $p
if($env:RUNTU_PRIVATE_KEY_PROTECT -eq '1'){
 if(Test-Path -LiteralPath $p -PathType Container){$a=[Security.AccessControl.DirectorySecurity]::new()}else{$a=[Security.AccessControl.FileSecurity]::new()}
 $a.SetAccessRuleProtection($true,$false)
 foreach($id in @($sid,$sys)){$a.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($id,'FullControl','Allow'))}
 if(Test-Path -LiteralPath $p -PathType Container){[IO.Directory]::SetAccessControl($p,$a)}else{[IO.File]::SetAccessControl($p,$a)}
 $a=Get-Acl -LiteralPath $p
}
if(!$a.AreAccessRulesProtected){throw 'Unprotected'}
foreach($rule in $a.Access){if($rule.AccessControlType -eq 'Allow' -and $rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value -notin @($sid.Value,$sys.Value)){throw 'Broad access'}}
Write-Output 'OK'
"""
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],env={**{k:v for k,v in os.environ.items() if k.lower()!='psmodulepath'},'PSModulePath':str(Path(os.environ['SystemRoot'])/'System32'/'WindowsPowerShell'/'v1.0'/'Modules'),'RUNTU_PRIVATE_KEY_TARGET':str(path.resolve()),'RUNTU_PRIVATE_KEY_PROTECT':'1' if protect else '0'},capture_output=True,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode or result.stdout.strip()!=b'OK':raise PrivateKeyError()

    def safe_path(self):
        for part in (self.path, *self.path.parents):
            if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
                raise PrivateKeyError()

    def read(self):
        try:
            self.safe_path()
            p=self.path
            if not p.is_file() or p.is_symlink() or p.parent.is_symlink():raise PrivateKeyError()
            signature=(p.stat().st_mtime_ns,p.stat().st_size)
            if self.cache and self.cache[0]==signature:return self.cache[1]
            self.access(p.parent);self.access(p)
            raw=p.read_bytes()
            if len(raw)>64:raise PrivateKeyError()
            Fernet(raw)
            secret=SecretStr(raw.decode('ascii'));self.cache=(signature,secret);return secret
        except Exception:raise PrivateKeyError() from None

    def provision(self):
        try:
            self.safe_path()
            if self.path.exists():return self.read()
            self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            self.access(self.path.parent,True)
            # Empty file is harmless until ACL protection has succeeded.
            fd=os.open(self.path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
            try:
                self.access(self.path,True)
                os.write(fd,Fernet.generate_key());os.fsync(fd)
            finally:os.close(fd)
            return self.read()
        except Exception:raise PrivateKeyError() from None
