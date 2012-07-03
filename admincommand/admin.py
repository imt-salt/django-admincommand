from django.contrib import admin
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.conf.urls.defaults import url
from django.core.urlresolvers import reverse
from django.http import HttpResponseBadRequest
from django.conf.urls.defaults import patterns
from django.utils.encoding import force_unicode
from django.utils.functional import update_wrapper
from django.http import HttpResponseForbidden

from sneak.admin import SneakAdmin

from admincommand.query import CommandQuerySet
from admincommand.models import AdminCommand as AdminCommandModel
from admincommand import core


class AdminCommandAdmin(SneakAdmin):
    QuerySet = CommandQuerySet
    list_display = ('command_name',)

    def get_urls(self):
        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        urlpatterns = patterns(
            '',
            url(
                r'^run/([\w_]+)',
                wrap(self.run_command_view),
            )
        )
        return urlpatterns + super(AdminCommandAdmin, self).get_urls()

    def run_command_view(self, request, command_name):
        admin_command = core.get_admin_commands()[command_name]

        if not request.user.has_perm(admin_command.permission_codename()):
            return HttpResponseForbidden()
        # original needed ``change_form`` context variables
        opts = self.model._meta
        app_label = opts.app_label

        help = admin_command.command().help

        ctx = {
            # original needed ``change_form.html`` context variables
            'module_name': force_unicode(opts.verbose_name_plural),
            'title': admin_command.command_name(),
            'is_popup': False,
            'root_path': None,
            'app_label': app_label,

            # ``run.html`` context
            'command_name': command_name,
            'help': help,
        }

        if request.method == 'POST':
            form = admin_command.form(request.POST)
            if form.is_valid():
                coreponse = core.run_command(
                    admin_command,
                    form.cleaned_data,
                    request.user
                )
                if not admin_command.asynchronous:
                    ctx['output'] = coreponse
                    return render(request, 'admincommand/output.html', ctx)
                path = reverse('admin:admincommand_admincommand_changelist')
                return HttpResponseRedirect(path)
        else:
            ctx['form'] = admin_command.form()
        return render(request, 'admincommand/run.html', ctx)

    def command_name(self, obj):
        """Used to populate admin change list row with a link to
        the form that of the command"""
        path = reverse('admin:admincommand_admincommand_changelist', )
        return '<a href="%srun/%s">%s: %s</a>' % (
            path,
            obj.command_name(),
            obj.command_name(),
            obj.command().help,
        )
    command_name.allow_tags = True

admin.site.register(AdminCommandModel, AdminCommandAdmin)