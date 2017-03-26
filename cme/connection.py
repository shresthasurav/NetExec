from traceback import format_exc
from gevent.coros import BoundedSemaphore
from functools import wraps
from cme.logger import CMEAdapter
from cme.context import Context

sem = BoundedSemaphore(1)
global_failed_logins = 0
user_failed_logins = {}

def requires_admin(func):
    def _decorator(self, *args, **kwargs):
        if self.admin_privs is False: return
        return func(self, *args, **kwargs)
    return wraps(func)(_decorator)

class connection:

    def __init__(self, args, db, host):
        self.args = args
        self.db = db
        self.host = host
        self.conn = None
        self.admin_privs = False
        self.hostname = None
        self.logger = None
        self.password = None
        self.username = None
        self.failed_logins = 0
        self.local_ip = None

        self.proto_flow()

    @staticmethod
    def proto_args(std_parser, module_parser):
        return

    def proto_logger(self):
        pass

    def enum_host_info(self):
        return

    def print_host_info(info):
        return

    def create_conn_obj(self):
        return

    def check_if_admin(self):
        return

    def plaintext_login(self, domain, username, password):
        return

    def hash_login(self, domain, username, ntlm_hash):
        return

    def proto_flow(self):
        if self.create_conn_obj():
            self.enum_host_info()
            self.proto_logger()
            self.print_host_info()
            if self.login():
                if hasattr(self.args, 'module') and self.args.module:

                    module_logger = CMEAdapter(extra={
                                                      'module': self.module.name.upper(),
                                                      'host': self.host,
                                                      'port': self.args.smb_port,
                                                      'hostname': self.hostname
                                                     })

                    context = Context(self.db, module_logger, self.args)
                    context.localip  = self.local_ip

                    if hasattr(self.module, 'on_request') or hasattr(self.module, 'has_response'):
                        self.server.context.localip = self.local_ip

                    if hasattr(self.module, 'on_login'):
                        self.module.on_login(context, self)

                    if self.admin_privs and hasattr(self.module, 'on_admin_login'):
                        self.module.on_admin_login(context, self)

                else:
                    for k, v in vars(self.args).iteritems():
                        if hasattr(self, k) and hasattr(getattr(self, k), '__call__'):
                            if v is not False and v is not None:
                                getattr(self, k)()

    def inc_failed_login(self, username):
        global global_failed_logins
        global user_failed_logins

        if username not in user_failed_logins.keys():
            user_failed_logins[username] = 0

        user_failed_logins[username] += 1
        global_failed_logins += 1
        self.failed_logins += 1

    def over_fail_limit(self, username):
        global global_failed_logins
        global user_failed_logins

        if global_failed_logins == self.args.gfail_limit: return True

        if self.failed_logins == self.args.fail_limit: return True

        if username in user_failed_logins.keys():
            if self.args.ufail_limit == user_failed_logins[username]: return True

        return False

    def login(self):
        for cred_id in self.args.cred_id:
            with sem:
                try:
                    c_id, credtype, domain, username, password = self.db.get_credentials(filterTerm=int(cred_id))[0]

                    if not domain: domain = self.domain

                    if self.args.local_auth:
                        domain = self.domain
                    elif self.args.domain:
                        domain = self.args.domain

                    if credtype == 'hash' and not self.over_fail_limit(username):
                        if self.hash_login(domain, username, password): return True

                    elif credtype == 'plaintext' and not self.over_fail_limit(username):
                        if self.plaintext_login(domain, username, password): return True

                except IndexError:
                    self.logger.error("Invalid database credential ID!")

        for user in self.args.username:
            if type(user) is file:
                for usr in user:
                    if self.args.hash:
                        with sem:
                            for ntlm_hash in self.args.hash:
                                if type(ntlm_hash) is not file:
                                    if not self.over_fail_limit(usr.strip()):
                                        if self.hash_login(self.domain, usr.strip(), ntlm_hash): return True

                                elif type(ntlm_hash) is file:
                                    for f_hash in ntlm_hash:
                                        if not self.over_fail_limit(usr.strip()):
                                            if self.hash_login(self.domain, usr.strip(), f_hash.strip()): return True
                                    ntlm_hash.seek(0)

                    elif self.args.password:
                        with sem:
                            for password in self.args.password:
                                if type(password) is not file:
                                    if not self.over_fail_limit(usr.strip()):
                                        if self.plaintext_login(self.domain, usr.strip(), password): return True

                                elif type(password) is file:
                                    for f_pass in password:
                                        if not self.over_fail_limit(usr.strip()):
                                            if self.plaintext_login(self.domain, usr.strip(), f_pass.strip()): return True
                                    password.seek(0)

            elif type(user) is not file:
                    if self.args.hash:
                        with sem:
                            for ntlm_hash in self.args.hash:
                                if type(ntlm_hash) is not file:
                                    if not self.over_fail_limit(user):
                                        if self.hash_login(self.domain, user, ntlm_hash): return True

                                elif type(ntlm_hash) is file:
                                    for f_hash in ntlm_hash:
                                        if not self.over_fail_limit(user):
                                            if self.hash_login(self.domain, user, f_hash.strip()): return True
                                    ntlm_hash.seek(0)

                    elif self.args.password:
                        with sem:
                            for password in self.args.password:
                                if type(password) is not file:
                                    if not self.over_fail_limit(user):
                                        if self.plaintext_login(self.domain, user, password): return True

                                elif type(password) is file:
                                    for f_pass in password:
                                        if not self.over_fail_limit(user):
                                            if self.plaintext_login(self.domain, user, f_pass.strip()): return True
                                    password.seek(0)