from oslo_config import cfg
from oslo_utils import uuidutils
from heat.db import api as db_api
from heat.common import exception
from heat.engine import stack as parser
from heat.engine import resources
from heat.engine import resource
from heat.engine import scheduler
from heat.common import context
from heat.common import identifier
import functools
import logging
import six

LOG = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s',
                    filename="purge_tool.log",
                    level=logging.INFO)

CONF = cfg.CONF

CONF.register_cli_opts([
    cfg.StrOpt('stack_name', default="", help='stack_name'),
    cfg.StrOpt('tenant_id', default="", help='tenant_id'),
    cfg.StrOpt('user', default="admin", help='user'),
], group='purge_tool')

CONF(project='heat', prog='heat-engine')
CONF(default_config_files=['purge_tool.conf'])

def store_context(func):
    @functools.wraps(func)
    def wrapped(self, *args, **kwargs):
        self.context.stack_id = self.id
        self.context.stack_name = self.name
        self.context.update_store()
        return func(self, *args, **kwargs)
    return wrapped


class OrgStack(parser.Stack):

    ACTIONS = ( DELETE ) = ( 'DELETE' )

    def state_set(self, action, status, reason):
        '''Update the stack state in the database.'''
        if action not in self.ACTIONS:
            raise ValueError(_("Invalid action %s") % action)

        if status not in self.STATUSES:
            raise ValueError(_("Invalid status %s") % status)

        self.action = action
        self.status = status
        self.status_reason = reason

        if self.id is None:
            return

        stack = db_api.stack_get(self.context, self.id)
        if stack is not None:
            stack.update_and_save({'action': action,
                                   'status': status,
                                   'status_reason': reason})
            msg = _('Stack %(action)s %(status)s (%(name)s): %(reason)s')
            LOG.info(msg % {'action': action,
                            'status': status,
                            'name': self.name,
                            'reason': reason})

    @store_context
    def delete(self, action=DELETE, backup=False, abandon=False):

        stack_status = self.COMPLETE
        reason = 'Stack %s completed successfully' % action
        self.state_set(action, self.IN_PROGRESS, 'Stack %s started' %
                       action)

        action_task = scheduler.DependencyTaskGroup(self.dependencies,
                                                    resource.Resource.destroy,
                                                    reverse=True)
        try:
            scheduler.TaskRunner(action_task)(timeout=self.timeout_secs())
        except exception.ResourceFailure as ex:
            stack_status = self.FAILED
            reason = 'Resource %s failed: %s' % (action, six.text_type(ex))
        except scheduler.Timeout:
            stack_status = self.FAILED
            reason = '%s timed out' % action.title()

        try:
            self.state_set(action, stack_status, reason)
        except exception.NotFound:
            LOG.info(_LI("Tried to delete stack that does not exist "
                         "%s "), self.id)

        if stack_status != self.FAILED:
            # delete the stack
            try:
                db_api.stack_delete(self.context, self.id)
            except exception.NotFound:
                LOG.info(_("Tried to delete stack that does not exist "
                           "%s ") % self.id)
            self.id = None



def dummy_context(user, tenant_id, password='passw0rd', roles=None, user_id=None, trust_id=None):
    roles = roles or []
    return context.RequestContext.from_dict({
        'tenant_id': tenant_id,
        'tenant': 'test_tenant',
        'username': user,
        'user_id': user_id,
        'password': password,
        'roles': roles,
        'is_admin': False,
        'auth_url': 'http://server.test:5000/v2.0',
        'auth_token': 'abcd1234',
        'trust_id': trust_id
    })


def _get_stack(cnxt, stack_id, show_deleted=False):
    s = db_api.stack_get(cnxt, stack_id,
                         show_deleted=show_deleted,
                         eager_load=True)

    if s is None:
        raise exception.StackNotFound(stack_name=stack_id)
    return s


def identify_stack(cnxt, stack_name):
    if uuidutils.is_uuid_like(stack_name):
        s = db_api.stack_get(cnxt, stack_name, show_deleted=True)
        if not s:
            s = db_api.stack_get_by_name(cnxt, stack_name)
    else:
        s = db_api.stack_get_by_name(cnxt, stack_name)
    if s:
        stack = parser.Stack.load(cnxt, stack=s)
        return dict(stack.identifier())
    else:
        raise exception.StackNotFound(stack_name=stack_name)

def abandon_stack(cnxt, stack_identity, abandon=True):
    st = _get_stack(cnxt, stack_identity)
    stack = OrgStack.load(cnxt, stack=st)
    stack_info = stack.delete(abandon=True)
    return stack_info


if __name__ == '__main__':
    ctx = dummy_context(CONF.purge_tool.user, CONF.purge_tool.tenant_id)
    db_stack = identify_stack(ctx, CONF.purge_tool.stack_name)
    abandon_stack(ctx, db_stack["stack_id"])
