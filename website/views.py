from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for, session, current_app
from flask_login import login_required, current_user
from .models import Note
from . import db
import json

#Aye Thiri Coding
from googleapiclient.discovery import build
from google.oauth2 import service_account
from datetime import datetime
import io
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError
import os

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle


OAUTHLIB_INSECURE_TRANSPORT = '1'

views = Blueprint('views', __name__)


@views.route('/')
@views.route('/home')
def home():
        return render_template("home.html" , user=current_user)

# @views.route('/dashboard')
# @login_required
# def dashboard():
#     return render_template("dashboard.html"  , user=current_user)

# Aye's Code - Dashboard Handler 
@views.route('/dashboard', endpoint='dashboard_view')
@login_required
def dashboard_view():
    if 'credentials' not in session:
        return redirect(url_for('views.authorize_view'))

    creds = Credentials(**session['credentials'])
    if not creds or not creds.valid:
        creds = refresh_credentials(creds)
        if not creds:
            return redirect(url_for('views.authorize_view'))

    service = build('drive', 'v3', credentials=creds)
    # Retrieve items here if needed
    return render_template('dashboard.html', items=[], user=current_user)

@views.route('/authorize', endpoint='authorize_view')
@login_required
def authorize_view():
    creds = load_credentials()
    if not creds:
        flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
        flow.redirect_uri = url_for('views.oauth2callback_view', _external=True)
        authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
        session['state'] = state
        return redirect(authorization_url)

    session['credentials'] = creds_to_dict(creds)
    return redirect(url_for('views.dashboard_view'))

@views.route('/oauth2callback', endpoint='oauth2callback_view')
@login_required
def oauth2callback_view():
    state = session.get('state')
    if not state:
        return "State not found", 400

    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES, state=state)
    flow.redirect_uri = url_for('views.oauth2callback_view', _external=True)
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)

    creds = flow.credentials
    session['credentials'] = creds_to_dict(creds)
    save_credentials(creds)

    return redirect(url_for('views.dashboard_view'))

@views.route('/search', methods=['GET'], endpoint='search_files')
@login_required
def search_files():
    query = request.args.get('query', '')
    folder = request.args.get('folder', '')
    file_type = request.args.get('file_type', '')
    uploaded_date = request.args.get('uploaded_date', '')

    if 'credentials' not in session:
        return redirect(url_for('views.authorize_view'))

    creds = Credentials(**session['credentials'])
    if not creds or not creds.valid:
        creds = refresh_credentials(creds)
        if not creds:
            return redirect(url_for('views.authorize_view'))

    service = build('drive', 'v3', credentials=creds)
    search_query = construct_search_query(query, folder, file_type, uploaded_date)

    try:
        results = service.files().list(
            q=search_query,
            fields="nextPageToken, files(id, name, mimeType, owners, createdTime, description)",
            spaces='drive'
        ).execute()
    except HttpError as e:
        current_app.logger.error(f"An error occurred during the search: {e}")
        return jsonify({'error': 'An error occurred during the search'}), 500

    items = results.get('files', [])
    formatted_items = format_search_results(items)

    return render_template('dashboard.html', items=formatted_items, user=current_user)

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

@views.route('/view/<file_id>', endpoint='view_file')
@login_required
def view_file(file_id):
    if 'credentials' not in session:
        return redirect(url_for('views.authorize_view'))

    creds = Credentials(**session['credentials'])
    if not creds or not creds.valid:
        creds = refresh_credentials(creds)
        if not creds:
            return redirect(url_for('views.authorize_view'))

    service = build('drive', 'v3', credentials=creds)

    try:
        file = service.files().get(fileId=file_id, fields='webViewLink').execute()
        view_link = file.get('webViewLink')

        if view_link:
            return redirect(view_link)
        else:
            return "File not found or view link not available", 404
    except HttpError as e:
        current_app.logger.error(f"An error occurred: {e}")
        return f"An error occurred: {e}", 500

@views.route('/list_files', endpoint='list_files_view')
@login_required
def list_files_view():
    if 'credentials' not in session:
        return redirect(url_for('views.authorize_view'))

    creds = Credentials(**session['credentials'])
    if not creds or not creds.valid:
        creds = refresh_credentials(creds)
        if not creds:
            return redirect(url_for('views.authorize_view'))

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
        current_app.logger.error(f"An error occurred during file listing: {e}")
        return jsonify({'error': str(e)}), 500

def load_credentials():
    creds = None
    token_path = 'token.pickle'

    if os.path.exists(token_path):
        with open(token_path, 'rb') as token_file:
            try:
                creds = pickle.load(token_file)
            except (pickle.PickleError, EOFError):
                current_app.logger.error("Error loading credentials from pickle file.")
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
        current_app.logger.error(f"Error refreshing credentials: {e}")
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


# Aye thiri pain's code 
# Google Drive API setup
secret_key = os.environ.get('FLASK_SECRET_KEY', '709c421d9b384d549070fa378f80926d')  # Use an environment variable for security

CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(__file__), "credentials.json")

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE', 'service_account.json')
print(f'Service account file path: {SERVICE_ACCOUNT_FILE}')


# Folder IDs for destination folders (Replace with actual IDs)
FOLDER_IDS = {
    'shared': os.getenv('SHARED_FOLDER_ID', '1RQ6dGBHOPPOBoa9A-cLURIeJZbyecUQY'),
    'archived': os.getenv('ARCHIVED_FOLDER_ID', '1azQ8WyDN9E5-IhYoxaM8qBxpqDY2zNSt'),
    'backup': os.getenv('BACKUP_FOLDER_ID', '1INe0sIpWSVwbQE-U8D1hTlkOm4rsghAY')
}

def authenticate():
    """Authenticate with Google Drive API using service account credentials."""
    try:
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        return creds
    except Exception as e:
        current_app.logger.error(f'Error during authentication: {str(e)}')
        raise

def format_date(date_str):
    """Format the date string to a readable format."""
    try:
        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return 'Unknown'

# @views.route('/', endpoint='home')
# def home():
#     return render_template('home.html')

@views.route('/upload', methods=['GET'], endpoint='upload_page')
@login_required
def upload_page():
    return render_template('upload.html', user=current_user)

@views.route('/upload', methods=['POST'], endpoint='handle_upload')
@login_required
def handle_upload():
    """Handle file upload and upload it to Google Drive."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'}), 400
    
    file = request.files['file']
    description = request.form.get('description', '')
    folder = request.form.get('folder', 'shared')

    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'}), 400

    if folder not in FOLDER_IDS:
        return jsonify({'success': False, 'message': 'Invalid folder selected'}), 400

    try:
        creds = authenticate()
        service = build('drive', 'v3', credentials=creds)

        file_metadata = {
            'name': file.filename,
            'parents': [FOLDER_IDS[folder]],
            'description': description
        }

        media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype=file.content_type)

        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, description, owners, createdTime'
        ).execute()

        return jsonify({
            'success': True,
            'file_id': uploaded_file.get('id'),
            'file_name': uploaded_file.get('name'),
            'message': 'File uploaded successfully!'
        })

    except HttpError as http_err:
        current_app.logger.error(f'HTTP error occurred during file upload: {str(http_err)}')
        return jsonify({'success': False, 'message': f'HTTP error occurred: {str(http_err)}'}), 500
    except Exception as e:
        current_app.logger.error(f'Error uploading file: {str(e)}')
        return jsonify({'success': False, 'message': f'An error occurred during upload: {str(e)}'}), 500

@views.route('/list_files', methods=['GET'], endpoint='list_files')
@login_required
def list_files():
    """List files in the Google Drive folders."""
    try:
        creds = authenticate()
        service = build('drive', 'v3', credentials=creds)

        query = " or ".join([f"'{folder_id}' in parents" for folder_id in FOLDER_IDS.values()])
        results = service.files().list(
            q=query,
            fields="files(id, name, description, owners, createdTime)",
            orderBy='createdTime desc'
        ).execute()

        files = results.get('files', [])

        formatted_files = []
        for file in files:
            owner = file['owners'][0]['displayName'] if 'owners' in file and file['owners'] else 'Unknown'
            uploaded_date = format_date(file.get('createdTime', ''))
            formatted_files.append({
                'id': file.get('id'),
                'name': file.get('name'),
                'description': file.get('description', 'No description'),
                'owner': owner,
                'uploaded_date': uploaded_date
            })

        return jsonify({
            'success': True,
            'files': formatted_files
        })
    
    except HttpError as http_err:
        current_app.logger.error(f'HTTP error occurred during file listing: {str(http_err)}')
        return jsonify({'success': False, 'message': f'HTTP error occurred: {str(http_err)}'}), 500
    except Exception as e:
        current_app.logger.error(f'Error listing files: {str(e)}')
        return jsonify({'success': False, 'message': f'Error listing files: {str(e)}'}), 500

@views.route('/update_description', methods=['POST'], endpoint='update_description')
@login_required
def update_description():
    """Update the description of a file in Google Drive."""
    try:
        data = request.get_json()
        file_id = data.get('fileId')
        description = data.get('description')

        if not file_id or description is None:
            return jsonify({'success': False, 'message': 'Invalid file ID or description'}), 400

        creds = authenticate()
        service = build('drive', 'v3', credentials=creds)

        file_metadata = {'description': description}

        updated_file = service.files().update(
            fileId=file_id,
            body=file_metadata,
            fields='id, name, description'
        ).execute()

        return jsonify({
            'success': True,
            'file_id': updated_file.get('id'),
            'description': updated_file.get('description'),
            'message': 'Description updated successfully!'
        })

    except HttpError as http_err:
        current_app.logger.error(f'HTTP error occurred during description update: {str(http_err)}')
        return jsonify({'success': False, 'message': f'HTTP error occurred: {str(http_err)}'}), 500
    except Exception as e:
        current_app.logger.error(f'Error updating description: {str(e)}')
        return jsonify({'success': False, 'message': f'Error updating description: {str(e)}'}), 500

@views.route('/share_file', methods=['POST'], endpoint='share_file_route')
@login_required
def share_file():
    """Share a file in Google Drive and return a view link."""
    try:
        data = request.get_json()
        file_id = data.get('fileId')

        if not file_id:
            return jsonify({'success': False, 'message': 'Invalid file ID'}), 400

        creds = authenticate()
        service = build('drive', 'v3', credentials=creds)

        permission = {
            'type': 'anyone',
            'role': 'reader'
        }
        service.permissions().create(fileId=file_id, body=permission).execute()

        file_metadata = service.files().get(fileId=file_id, fields='webViewLink').execute()
        view_link = file_metadata.get('webViewLink')

        return jsonify({
            'success': True,
            'message': 'File shared successfully!',
            'viewLink': view_link
        })

    except HttpError as http_err:
        current_app.logger.error(f'HTTP error occurred during file sharing: {str(http_err)}')
        return jsonify({'success': False, 'message': f'HTTP error occurred: {str(http_err)}'}), 500
    except Exception as e:
        current_app.logger.error(f'Error sharing file: {str(e)}')
        return jsonify({'success': False, 'message': f'Error sharing file: {str(e)}'}), 500

@views.route('/delete_file', methods=['POST'], endpoint='delete_file')
@login_required
def delete_file():
    """Delete a file in Google Drive."""
    try:
        data = request.get_json()
        file_id = data.get('fileId')

        if not file_id:
            return jsonify({'success': False, 'message': 'Invalid file ID'}), 400

        creds = authenticate()
        service = build('drive', 'v3', credentials=creds)

        # Verify if the file exists before deleting
        try:
            service.files().get(fileId=file_id).execute()
        except HttpError as e:
            if e.resp.status == 404:
                return jsonify({'success': False, 'message': 'File not found'}), 404
            else:
                raise

        service.files().delete(fileId=file_id).execute()

        return jsonify({'success': True, 'message': 'File deleted successfully!'})

    except HttpError as http_err:
        current_app.logger.error(f'HTTP error occurred during file deletion: {str(http_err)}')
        return jsonify({'success': False, 'message': f'HTTP error occurred: {str(http_err)}'}), 500
    except Exception as e:
        current_app.logger.error(f'Error deleting file: {str(e)}')
        return jsonify({'success': False, 'message': f'Error deleting file: {str(e)}'}), 500

# End of the Aye thiri's Code


@views.route('/note', methods=['GET', 'POST'])
@login_required
def note():
    if request.method == 'POST': 
        note = request.form.get('note')#Gets the note from the HTML 

        if len(note) < 1:
            flash('Note is too short!', category='error') 
        else:
            new_note = Note(data=note, user_id=current_user.id)  #providing the schema for the note 
            db.session.add(new_note) #adding the note to the database 
            db.session.commit()
            flash('Note added!', category='success')

    return render_template("note.html", user=current_user)


@views.route('/delete-note', methods=['POST'])
@login_required
def delete_note():  
    note = json.loads(request.data) # this function expects a JSON from the INDEX.js file 
    noteId = note['noteId']
    note = Note.query.get(noteId)
    if note:
        if note.user_id == current_user.id:
            db.session.delete(note)
            db.session.commit()

    return jsonify({})
