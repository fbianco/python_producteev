#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Copyright © 2014 François Bianco <francois.bianco@skadi.ch>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

See COPYING file for the full license.

"""

import argparse
import gzip
import sys

import httplib2
from urllib import urlencode
import simplejson as json

from oauth2client.file import Storage
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import OAuth2WebServerFlow
from oauth2client import tools

DEBUG = False

"""
API Key
-------

To get an API key, please go to https://www.producteev.com/settings/apps
with http://localhost:8080 as redirect uri.
"""
CLIENT_ID     = 'required'
CLIENT_SECRET = 'required'

"""API URI"""
API_URI    = 'https://www.producteev.com'
AUTH_URI   = API_URI + '/oauth/v2/auth'
TOKEN_URI  = API_URI + '/oauth/v2/token'
REVOKE_URI = API_URI + '/oauth/v2/revoke' # FIXME not sure if it exists

REDIRECT_URI  = 'http://localhost:8080' # oauth2client serveur


"""Producteev Exceptions"""
class ProducteevError(Exception): pass
class ProducteevNotImplemented(ProducteevError): pass
class ProducteevBadRequest(ProducteevError): pass # HTTP 400
class ProducteevUnauthorized(ProducteevError): pass # HTTP 401
class ProducteevAccessDenied(ProducteevError): pass # HTTP 403
class ProducteevNotFound(ProducteevError): pass # HTTP 404
class ProducteevConflict(ProducteevError): pass # HTTP 409
class ProducteevInternalServerError(ProducteevError): pass # HTTP 500
class ProducteevUnknown(ProducteevError): pass


class Producteev():
    """Producteev python API"""

    def __init__(self, client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URI):
        """Create the Producteev python API based on their REST API

           client_id, client_secret are the API key for the application

        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.http = httplib2.Http()
        self.auth()

    # O2AUTH
    def auth(self):
        """Get authentification token from standard OAuth 2.0 flow

           This function store the authentification token in a local file,
           and create an authentificated Http request by adding the OAuth
           token to the headers.

        """
        flow = OAuth2WebServerFlow(self.client_id, self.client_secret,
                                    scope = '',
                                    redirect_uri = self.redirect_uri,
                                    auth_uri = AUTH_URI,
                                    token_uri = TOKEN_URI,
                                    revoke_uri = REVOKE_URI
                                   )

        storage = Storage('credentials_producteev.dat')
        credentials = storage.get()
        parser = argparse.ArgumentParser(parents=[tools.argparser])
        flags = parser.parse_args()

        if credentials is None or credentials.invalid:
            credentials = tools.run_flow(flow, storage, flags)
        self.http = credentials.authorize(self.http)


    # HTTP
    def request(self, uri, method, headers=None, body=None):
        """Send the authentificated request to the Producteev API and
           deal with error code and JSON conversion of response.

           headers and body are already urlencoded!
           method are standards HTTP methods
        """
        r,c = self.http.request(API_URI + uri, method, headers=headers, body=body)

        if DEBUG:
            print "Request:", uri, headers, body
            print "Response:", r, c
        s = int(r['status'])
        try:
            c = json.loads(c)
        except json.JSONDecodeError:
            pass

        # Success
        if   200 == s:
            return c
        elif 201 == s:
            return c
        elif 204 == s:
            # Your request was processed but doesn't return any information/object (e.g when you delete an object)
            return None

        # Redirection
        if 302 == s:
            try:
                # FIXME Hack to trim access_token, else we get
                #       an HTTP error 500 since the access_token
                #       is repeated in headers...
                #       Problem reported to Producteev
                return self.GET(r['location'].split('?')[0])
            except KeyError:
                s = 404
                c = r

        # Error
        if DEBUG: print 'ERROR: request failled at URI', uri

        if   400 == s:
            raise ProducteevBadRequest, c
        elif 401 == s:
            raise ProducteevUnauthorized, c
        elif 403 == s:
            raise ProducteevAccessDenied, c
        elif 404 == s:
            raise ProducteevNotFound, c
        elif 409 == s:
            raise ProducteevConflict, c
        elif 500 == s:
            raise ProducteevInternalServerError, c
        else:
            raise ProducteevUnknown, c

    def _HTTP(self, uri, method, json_obj=None):
        """Helper function for HTTP method taking care to encode JSON obj into
           string if it was not already done.

           If json_obj is not a str, unicode or a valid json object will
           propagate the JSON exception ValueError.
        """
        if json_obj:
            if not type(json_obj) in (unicode, str):
                json_obj = json.dumps(json_obj)
            return self.request(uri, method, {'Content-Type': 'application/json'}, json_obj)
        else:
            return self.request(uri, method)

    def GET(self, uri, json_obj=None): return self._HTTP(uri, 'GET', json_obj)
    def DELETE(self, uri, json_obj=None): return self._HTTP(uri, 'DELETE', json_obj)
    def POST(self, uri, json_obj=None): return self._HTTP(uri, 'POST', json_obj)
    def PUT(self, uri, json_obj=None): return self._HTTP(uri, 'PUT', json_obj)

    # ANNOUNCEMENTS
    #   https://api.producteev.com/api/doc/#Announcements
    def get_unread_announcement(self):
        return self.GET('/api/announcements/unread')

    def get_announcement(self, announcement_id):
        return self.GET('/api/announcements/{0}'.format(announcement_id))

    def mark_announcement_read(self, announcement_id):
        return self.PUT('/api/api/announcements/{0}/read'.format(announcement_id))


    # FILES
    #   https://api.producteev.com/api/doc/#Files
    def get_file(self, file_id):
        return self.GET('/api/files/{0}'.format(file_id))

    def delete_file(self, file_id):
        return self.DELETE('/api/files/{0}'.format(file_id))

    def preview_file(self, file_id):
        return self.GET('/api/files/{0}/view'.format(file_id))

    def upload_file(self, file_path):
        if not 'multipart' in sys.modules:
            import multipart
        with open(file_path,'r') as f:
            content_type, body = multipart.get_content_type_and_body({}, {'file': ('file', f)})
            return self.request('/api/upload/files', 'POST',  {'Content-Type': content_type}, body)

    def upload_remote_file(self, file_name, file_uri):
        return self.POST('/api/upload/remotefiles', {"remoteFile":{"url":file_uri,"fileName":file_name}})

    # LABELS
    #   https://api.producteev.com/api/doc/#Labels
    def get_label_colors(self):
        return self.GET('/api/label_colors')

    def create_label(self, title, foreground_color, background_color, network_id):
        label = {
                "label":{
                    "title": title,
                    "foreground_color": foreground_color,
                    "background_color": background_color,
                    "network": {
                        "id": network_id
                    }
                }
            }
        return self.POST('/api/labels', label)

    def get_label(self, label_id):
        return self.GET('/api/labels/{0}'.format(label_id))

    def update_label(self, label_id, **kwargs):
        """Update label from keywords arguments"""
        return self.PUT('/api/labels/{0}'.format(label_id), {"label":kwargs})

    def delete_label(self, label_id):
        return self.DELETE('/api/labels/{0}'.format(label_id), 'DELETE')


    # LANGUAGES
    #   https://api.producteev.com/api/doc/#Languages
    def get_languages(self):
        return self.GET('/api/languages')


    # SUGGESTIONS
    #   https://api.producteev.com/api/doc/#NLP%20Suggestions
    def get_npl_suggestions(self, query, project_id):
        return self.GET('/api/nlp_suggestions/{0}?' + urlencode({'query':query}))


    # NETWORK INVITATIONS
    #   https://api.producteev.com/api/doc/#Network%20Invitations
    def get_invitations(self, invitation_type):
        """Get the list of pending invitation for the current user
           invitation_type = requests|authorizations
        """
        return self.GET('/api/network_invitations?' + urlencode({'type':invitation_type}))

    def invite_user(self, user_email, invitation_type, network_id):
        """Invite a user to join the network. You can use the user id or an email address
           invitation_type = member|admin
        """
        invitation = {
          "network_invitation":{
            "email":email,
            "type":invitation_type,
            "network":{"id":network_id}
          }
        }
        return self.POST('/api/network_invitations', invitation)

    def invitation_reply(self, invitation_id, status):
        """Accept or refuse an invitation to join a network.

          status = - pending - confirmed - refused - waiting_for_admin - revoked - not_authorized_by_admin
        """
        return self.PUT('/api/network_invitations/{0}'.format(invitation_id), {"network_invitation":{"status":status}})

    def add_project_invitation(self, network_id, project_id):
        """Add a restricted project to a network invitation"""
        return self.POST('/api/network_invitations/{0}/projects/{1}'.format(network_id, project_id))

    def resend_invitation(self, invitation_id):
        """Re-send the email for a network invitation"""
        return self.POST('/api/network_invitations/{0}/resend'.format(invitation_id))

    # NETWORK
    #   https://www.producteev.com/api/doc/#Networks
    def get_networks(self,page=1, per_page=50, admin_only=False):
        """Get all the networks of the user
           The call is paginated.

           admin_only: Include only networks that user is an administrator of (default=false)
        """
        return self.GET('/api/networks?' + urlencode({'page':page, 'per_page':per_page, 'admin_only':admin_only}))

    def create_network(self, title, visible=True, auto_join=False, company_name='', company_size=1):
        network = {
                    "network":{
                        "title": title,
                        "visible": visible,
                        "auto_join": auto_join,
                        "company_size": company_size,
                        "company_name": company_name
                      }
                  }
        return self.POST('/api/networks', network)

    def get_network(self, network_id):
        return self.GET('/api/networks/{0}'.format(network_id))

    def update_network(self, network_id, **kwargs):
        """Update network values from given keywords arguments:
           title, visible, auto_join, company_size, company_name
         """
        return self.PUT('/api/networks/{0}'.format(network_id), {"Network":kwargs})

    def delete_network(self, network_id):
        """This will delete all tasks, projects and labels. You must be careful
           when you remove a network because some restricted projects that you
           do not see can be inside this network. You must be an admin of the
           network to delete it.
        """
        return self.DELETE('/api/networks/{0}'.format(network_id))

    def get_network_admins(self, network_id, page=1, per_page=50):
        """Retrieve the list of the network admins
           This call is paginated
        """
        return self.GET('/api/networks/{0}/admins'.format(network_id) + '?' + urlencode({'page':page, 'per_page':per_page}))

    def set_network_admin(self, network_id, user_id):
        return self.PUT('/api/networks/{0}/admins/{0}').format(network_id, user_id)

    def delete_network_admin(self, network_id, user_id):
        return self.DELETE('/api/networks/{0}/admins/{0}').format(network_id, user_id)

    def get_network_labels(self, network_id, page=1, per_page=50):
       """Retrieve the list of the network labels
          This call is paginated
       """
       return self.GET('/api/networks/{0}/labels'.format(network_id) + '?' + urlencode({'page':page, 'per_page':per_page}))

    def search_network_labels(self, network_id, search_query, page=1, per_page=50):
       """Search for Labels inside a network
          This call is paginated
       """
       return self.GET('/api/networks/{0}/labels/search'.format(network_id) + '?' + urlencode({'search':search_query, 'page':page, 'per_page':per_page}))

    def get_network_invitations(self, network_id):
        return self.GET('/api/networks/{0}/network_invitations'.format(network_id))

    def get_network_projects(self, project_type='all', page=1, per_page=50):
        """Search for Labels inside a network
           This call is paginated

           You can specify the type of projects you want to be returned:
            "all", "following" or "private".
        """
        return self.GET('/api/networks/{0}/projects'.format(network_id) + '?' + urlencode({'type': project_type, 'page':page, 'per_page':per_page}))

    def search_network_projects(self, network_id, search_query, page=1, per_page=50):
       """ Search for Projects inside a network
           This call is paginated
       """
       return self.GET('/api/networks/{0}/projects/search'.format(network_id) + '?' + urlencode({'search':search_query, 'page':page, 'per_page':per_page}))

    def get_network_users(self, network_id, page=1, per_page=50):
        """Retrieve the list of the users of the network.
           This call is paginated
        """
        return self.GET('/api/networks/{0}/users'.format(network_id)  + '?' + urlencode({'page':page, 'per_page':per_page}))

    def search_network_users(self, network_id, search_query, page=1, per_page=50):
       """ Search for users inside a network
           This call is paginated
       """
       return self.GET('/api/networks/{0}/users/search'.format(network_id) + '?' + urlencode({'search':search_query, 'page':page, 'per_page':per_page}))

    def delete_network_user(self, network_id, user_id):
        return self.DELETE('/api/networks/{0}/users/{0}'.format(network_id, user_id))

    
    # NOTES
    #   https://www.producteev.com/api/doc/#Notes
    def create_note(self, message, task_id, files_list=[]):
        note = {
            "note":{
                "message":message,
                "files":files_list, # [{'id':file1_id},{'id':file2_id}]
                "task":{"id":task_id}
            }
        }
        return self.POST('/api/notes', note)

    def get_note(self, note_id):
        return self.GET('/api/notes/{0}'.format(note_id))

    def update_note(self, note_id, **kwargs):
        """Update a note from keywords arguments"""
        return self.PUT('/api/notes/{0}'.format(note_id), {'note':kwargs})

    def delete_note(self, note_id):
        return self.DELETE('/api/notes/{0}'.format(note_id))

    # NOTIFICATIONS
    #   https://www.producteev.com/api/doc/#Notifications

    # TODO implement

    # PREMIUM
    #   https://www.producteev.com/api/doc/#Premium

    # TODO implement

    # PRICE
    #   https://www.producteev.com/api/doc/#Prices

    # TODO implement

    # PROJECT
    #   https://www.producteev.com/api/doc/#Projects
    def create_project(self, title, description, restricted, locked, network_id ):
        project = json.dumps({
                    "project":{
                      "title":title,
                      "description":description,
                      "restricted":restricted,
                      "locked":locked,
                      "network":{"id":network_id}
                    }
                  })
        return self.POST('/api/projects', project)

    def get_project(self, project_id):
        return self.GET('/api/projects/{0}'.format(project_id))

    def update_project(self, project_id, title=None, description=None, restricted=None, locked=None, network_id=None):
        project = self.GET_project(project_id)
        if title:
            project['title'] = title
        if description:
            project['description'] = description
        if restricted:
            project['restricted'] = restricted
        if locked:
            project['locked'] = locked
        if network_id:
            project['network']['id'] = network_id

        return self.PUT('/api/projects/{0}'.format(project_id), json.dumps(project))

    def delete_project(self, project_id):
        return self.DELETE('/api/projects/{0}'.format(project_id))

    def get_project_activities(self, project_id, page=1, per_page=50):
        """Get all the activities happening in a project 

           This call is paginated
           Note: page > 0, max(per_page) = 50
        """
        return self.GET('/api/projects/{0}/activities'.format(project_id) + '?' + urlencode({'page':page,'per_page':per_page}))

    def get_project_admins(self, project_id):
        return self.GET('/api/projects/{0}/admins'.format(project_id))

    def add_project_admin(self, project_id, admin_id):
        return self.PUT('/api/projects/{0}/admins/{1}'.format(project_id, admin_id))

    def remove_project_admin(self, project_id, admin_id):
        return self.DELETE('/api/projects/{0}/admins/{1}'.format(project_id, admin_id))

    def get_project_followers(self, project_id, page=1, per_page=50):
        """Retrieve the list of the followers of the project.

           This call is paginated
           Note: page > 0, max(per_page) = 50
        """
        return self.GET('/api/projects/{0}/followers'.format(project_id) + '?' + urlencode({'page':page,'per_page':per_page}))

    def add_project_follower(self, project_id, follower_id):
        return self.PUT('/api/projects/{0}/followers/{1}'.format(project_id, follower_id))

    def remove_project_follower(self, project_id, follower_id):
        return self.DELETE('/api/projects/{0}/followers/{1}'.format(project_id, follower_id))

    def get_project_restricted_users(self, project_id):
        return self.GET('/api/projects/{0}/restricted_users'.format(project_id))

    def add_project_restricted_users(self, project_id, user_id):
        return self.PUT('/api/projects/{0}/restricted_users/{1}'.format(project_id, user_id))

    def remove_project_restricted_users(self, project_id, user_id):
        return self.DELETE('/api/projects/{0}/restricted_users/{1}'.format(project_id, user_id))


    # TASKS
    #   https://www.producteev.com/api/doc/#Tasks
    def create_task(self, title, project_id):
        task = {
                "task":{
                    "title":title,
                    "project": {"id":project_id}
                    }
                }
        return self.POST('/api/tasks', task)

    def update_tasks(self, tasks_list):
        return self.POST('/api/tasks', json.dumps(tasks_list))

    def delete_tasks(self, tasks_list):
        return self.DELETE('/api/tasks', tasks_list)

    def export_tasks(self, criteria='', filters={'alias':'all','sort':'created_at','order':'desc'}):
        """
        Return the location of a CVS exported file with all
        the tasks matching the criteria and filters given.

        By default it will return the list of all active tasks.

        In case of success the request return in the header the location
        302 Location: /api/files/{id}?access_token=...

        Criteria is a JSON object:
            {
            "networks":["id1", "id2"],
            "projects":["id1", "id2"],
            "priorities":[1, 2, 3, 4, 5],
            "statuses":[0, 1],
            "responsibles":["id1", "id2"],
            "followers":["id1", "id2"],
            "creators":["id1", "id2"],
            "labels":["id1", "id2"],
            "deadline":{"from":123456789, "to":12345678910},
            "created_at":{"from":123456789, "to":12345678910},
            "updated_at":{"from":123456789, "to":12345678910},
            "search":{"text": "foo"}
            }

        Whereas filters is a dictionary of key-value which are use as query parameters:

        example : {'alias':'all','sort':'created_at','order':'desc'}

        alias: active|activeandcompleted|all|starred|completed|created|responsible|following|duetoday|duethisweek|late|files
        sort: created_at|updated_at|project|creator|deadline_time|priority|status|title
        order: asc|desc
        include_deleted: Include deleted task in the search results (default=false)

        For more details and other filters options see https://www.producteev.com/api/doc/#Search

        """
        return self.POST('/api/tasks/export?' + urlencode(filters), criteria)

    def add_tasks_label(self, tasks_list, label_id):
        """Add a label to a list of tasks"""
        return self.PUT('/api/tasks/labels/{0}'.format(label_id), tasks_list)

    def add_tasks_user(self, tasks_list, user_id):
        """Add a Responsible to a list of tasks"""
        return self.PUT('/api/tasks/responsibles/{user_id}'.format(user_id), tasks_list)

    def search_tasks(self, criteria='', filters={'alias':'all','sort':'created_at','order':'desc'}, page=1, per_page=50):
        """Return a list of tasks matching search criteria and filters.
           For details about criteria and filters see self.export_tasks()

           This request is paginated.
        """
        return self.POST('/api/tasks/search?' + urlencode(filters) + '&' + urlencode({'page':page,'per_page':per_page}), criteria)

    def get_tasks_alias_counts(self):
        """Return the number of tasks for each alias"""
        return self.POST('/api/tasks/search/counts')

    def get_task(self, task_id):
        return self.GET('/api/tasks/{0}'.format(task_id))

    def update_task(self, task_id, **kwargs):
        """Update given task by changing the task attributes passed as
           keywords arguments
        """
        return self.PUT('/api/tasks/{0}'.format(task_id), json.dumps({"task":kwargs}))

    def delete_task(self, task_id):
        return self.DELETE('/api/tasks/{0}'.format(task_id))

    def get_task_activities(self, task_id, page=1, per_page=50):
        """
            Get the task activities
            This is paginated
        """
        return self.GET('/api/tasks/{0}/activities'.format(task_id) + '?' + urlencode({'page':page,'per_page':per_page}))

    def add_task_follower(self, task_id, user_id):
        return self.PUT('/api/tasks/{0}/followers/{1}'.format(task_id, user_id))

    def delete_task_follower(self, task_id, user_id):
        return self.DELETE('/api/tasks/{0}/followers/{1}'.format(task_id, user_id))

    def add_task_label(self, task_id, label_id):
        return self.PUT('/api/tasks/{0}/labels/{1}'.format(task_id, label_id))

    def delete_task_label(self, task_id, label_id):
        return self.DELETE('/api/tasks/{0}/labels/{1}'.format(task_id, label_id))

    def get_task_notes(self, task_id):
        return self.GET('/api/tasks/{0}/notes'.format(task_id))

    def add_task_responsible(self, task_id, user_id):
        return self.PUT('/api/tasks/{0}/responsibles/{1}'.format(task_id, user_id))

    def delete_task_responsible(self, task_id, user_id):
        return self.DELETE('/api/tasks/{0}/responsibles/{1}'.format(task_id, user_id))

    def create_subtask(self, task_id, title, status=1):
        """Create a new subtask in a task"""
        subtask = { "subtask":{
                        "title":"Review the copy",
                        "status":1
                        }
                  }
        return self.POST('/api/tasks/{0}/subtasks'.format(task_id), subtask)

    def update_subtask(self, task_id, subtask_id, **kwargs):
        """Update a subtask in a task form keywords arguments"""
        return self.PUT('/api/tasks/{0}/subtasks/{0}'.format(task_id, subtask_id), {'subtask':kwargs})

    def delete_subtask(self, task_id, subtask_id):
        return self.DELETE('/api/tasks/{0}/subtasks/{0}'.format(task_id, subtask_id))


    # THEMES
    #   https://www.producteev.com/api/doc/#Themes

    # TODO implement


    # TIMEZONES
    #   https://www.producteev.com/api/doc/#Timezones
    def get_timezones(self):
        return self.GET('/api/timezones')


    # USERS
    #   https://www.producteev.com/api/doc/#Users

    def get_current_user(self):
        return self.GET('/api/users/me')

    def update_current_user(self, **kwargs):
        """
            Update the current logged in user
            from keywords arguments
        """
        return self.PUT('/api/users/me',{"user":kwargs})

    def upload_avatar(self, file_path):
        if not 'multipart' in sys.modules:
            import multipart
        with open(file_path,'r') as f:
            content_type, body = multipart.get_content_type_and_body({}, {'avatar': ('avatar', f)})
            return self.request('/api/users/me/avatar', 'POST',  {'Content-Type': content_type}, body)

    def get_default_project(self):
        """Retrieve the current user's default project"""
        return self.GET('/api/users/me/default_project')

    def update_default_project(self, project_id):
        """Change the current user default project"""
        return self.PUT('/api/users/me/default_project/{0}'.format(project_id))

    def upload_remote_avatar(self, file_url):
        return self.POST('/api/users/me/remoteavatar', {"remoteFile":{"url":file_url}})

    def search_users(self, email, exclude_loggedin_user=True, page=1, per_page=50):
        """Search users across all your networks by email address
           The result is paginated
        """
        return self.GET('/api/users/search?' + urlencode({'email':email,'exclude_loggedin_user':exclude_loggedin_user,'page':page,'per_page':per_page}))

    def get_user(self, user_id):
        return self.GET('/api/users/{id}'.format(user_id))

