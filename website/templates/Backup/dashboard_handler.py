import os
import pickle
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Allow OAuthlib to use HTTP during local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get('FLASK_SECRET_KEY', '709c421d9b384d549070fa378f80926d')  # Use an environment variable for security

    CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(__file__), "credentials.json")
    SCOPES = ['https://www.googleapis.com/auth/drive']

    FOLDER_IDS = {
        'shared': os.getenv('SHARED_FOLDER_ID', '1RQ6dGBHOPPOBoa9A-cLURIeJZbyecUQY'),
        'archived': os.getenv('ARCHIVED_FOLDER_ID', '1azQ8WyDN9E5-IhYoxaM8qBxpqDY2zNSt'),
        'backup': os.getenv('BACKUP_FOLDER_ID', '1INe0sIpWSVwbQE-U8D1hTlkOm4rsghAY')
    }

    @app.route('/dashboard', endpoint='dashboard_view')
    def dashboard_view():
        if 'credentials' not in session:
            return redirect(url_for('authorize_view'))

        creds = Credentials(**session['credentials'])
        if not creds or not creds.valid:
            creds = refresh_credentials(creds)
            if not creds:
                return redirect(url_for('authorize_view'))

        service = build('drive', 'v3', credentials=creds)
        # Retrieve items here if needed
        return render_template('dashboard.html', items=[])

    @app.route('/authorize', endpoint='authorize_view')
    def authorize_view():
        creds = load_credentials()
        if not creds:
            flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            flow.redirect_uri = url_for('oauth2callback_view', _external=True)
            authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
            session['state'] = state
            return redirect(authorization_url)

        session['credentials'] = creds_to_dict(creds)
        return redirect(url_for('dashboard_view'))

    @app.route('/oauth2callback', endpoint='oauth2callback_view')
    def oauth2callback_view():
        state = session.get('state')
        if not state:
            return "State not found", 400

        flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES, state=state)
        flow.redirect_uri = url_for('oauth2callback_view', _external=True)
        authorization_response = request.url
        flow.fetch_token(authorization_response=authorization_response)

        creds = flow.credentials
        session['credentials'] = creds_to_dict(creds)
        save_credentials(creds)

        return redirect(url_for('dashboard_view'))

    @app.route('/search', methods=['GET'], endpoint='search_files')
    def search_files():
        query = request.args.get('query', '')
        folder = request.args.get('folder', '')
        file_type = request.args.get('file_type', '')
        uploaded_date = request.args.get('uploaded_date', '')

        if 'credentials' not in session:
            return redirect(url_for('authorize_view'))

        creds = Credentials(**session['credentials'])
        if not creds or not creds.valid:
            creds = refresh_credentials(creds)
            if not creds:
                return redirect(url_for('authorize_view'))

        service = build('drive', 'v3', credentials=creds)
        search_query = construct_search_query(query, folder, file_type, uploaded_date)

        try:
            results = service.files().list(
                q=search_query,
                fields="nextPageToken, files(id, name, mimeType, owners, createdTime, description)",
                spaces='drive'
            ).execute()
        except HttpError as e:
            app.logger.error(f"An error occurred during the search: {e}")
            return jsonify({'error': 'An error occurred during the search'}), 500

        items = results.get('files', [])
        formatted_items = format_search_results(items)

        return render_template('dashboard.html', items=formatted_items)

    def construct_search_query(query, folder, file_type, uploaded_date):
        search_query = f"name contains '{query}'"
        if folder:
            folder_id = FOLDER_IDS.get(folder)
            if folder_id:
                search_query += f" and '{folder_id}' in parents"
        if file_type:
            if file_type == 'image':
                search_query += " and (mimeType = 'image/jpeg' or mimeType = 'image/png' or mimeType = 'image/gif')"
            else:
                search_query += f" and mimeType = '{file_type}'"
        if uploaded_date:
            search_query += f" and createdTime >= '{uploaded_date}T00:00:00'"

        return search_query

    def format_search_results(items):
        formatted_items = []
        for item in items:
            formatted_items.append({
                'id': item.get('id'),
                'name': item.get('name'),
                'owner': ', '.join(owner.get('displayName', 'Unknown') for owner in item.get('owners', [])),
                'uploaded_date': item.get('createdTime', '').split('T')[0],
                'description': item.get('description', '')
            })
        return formatted_items

    @app.route('/view/<file_id>', endpoint='view_file')
    def view_file(file_id):
        if 'credentials' not in session:
            return redirect(url_for('authorize_view'))

        creds = Credentials(**session['credentials'])
        if not creds or not creds.valid:
            creds = refresh_credentials(creds)
            if not creds:
                return redirect(url_for('authorize_view'))

        service = build('drive', 'v3', credentials=creds)

        try:
            file = service.files().get(fileId=file_id, fields='webViewLink').execute()
            view_link = file.get('webViewLink')

            if view_link:
                return redirect(view_link)
            else:
                return "File not found or view link not available", 404
        except HttpError as e:
            app.logger.error(f"An error occurred: {e}")
            return f"An error occurred: {e}", 500

    @app.route('/list_files', endpoint='list_files_view')
    def list_files_view():
        if 'credentials' not in session:
            return redirect(url_for('authorize_view'))

        creds = Credentials(**session['credentials'])
        if not creds or not creds.valid:
            creds = refresh_credentials(creds)
            if not creds:
                return redirect(url_for('authorize_view'))

        service = build('drive', 'v3', credentials=creds)

        try:
            results = service.files().list(
                fields="nextPageToken, files(id, name, mimeType, owners, createdTime, description)",
                spaces='drive'
            ).execute()
            items = results.get('files', [])
            formatted_items = format_search_results(items)
            return jsonify(formatted_items)
        except HttpError as e:
            app.logger.error(f"An error occurred during file listing: {e}")
            return jsonify({'error': str(e)}), 500

    def load_credentials():
        creds = None
        token_path = 'token.pickle'

        if os.path.exists(token_path):
            with open(token_path, 'rb') as token_file:
                try:
                    creds = pickle.load(token_file)
                except (pickle.PickleError, EOFError):
                    app.logger.error("Error loading credentials from pickle file.")
                    creds = None

        if creds and creds.expired and creds.refresh_token:
            creds = refresh_credentials(creds)
            if not creds:
                return None

        return creds

    def save_credentials(creds):
        token_path = 'token.pickle'
        with open(token_path, 'wb') as token_file:
            pickle.dump(creds, token_file)

    def refresh_credentials(creds):
        try:
            creds.refresh(Request())
            save_credentials(creds)
            session['credentials'] = creds_to_dict(creds)
            return creds
        except RefreshError as e:
            app.logger.error(f"Error refreshing credentials: {e}")
            session.pop('credentials', None)
            if os.path.exists('token.pickle'):
                os.remove('token.pickle')
            return None

    def creds_to_dict(creds):
        return {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        }

    return app
