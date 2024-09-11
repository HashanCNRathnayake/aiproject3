from flask import Flask, render_template, request, jsonify, redirect, url_for
from googleapiclient.discovery import build
from google.oauth2 import service_account
from datetime import datetime
import io
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError
import os
from dashboard_handler import create_app

# Initialize Flask app using create_app from dashboard_handler.py
app = create_app()

# Google Drive API setup
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE', 'service_account.json')

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
        app.logger.error(f'Error during authentication: {str(e)}')
        raise

def format_date(date_str):
    """Format the date string to a readable format."""
    try:
        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return 'Unknown'

@app.route('/', endpoint='home')
def home():
    return render_template('home.html')

@app.route('/dashboard', endpoint='dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/upload', methods=['GET'], endpoint='upload_page')
def upload_page():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'], endpoint='handle_upload')
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
        app.logger.error(f'HTTP error occurred during file upload: {str(http_err)}')
        return jsonify({'success': False, 'message': f'HTTP error occurred: {str(http_err)}'}), 500
    except Exception as e:
        app.logger.error(f'Error uploading file: {str(e)}')
        return jsonify({'success': False, 'message': f'An error occurred during upload: {str(e)}'}), 500

@app.route('/list_files', methods=['GET'], endpoint='list_files')
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
        app.logger.error(f'HTTP error occurred during file listing: {str(http_err)}')
        return jsonify({'success': False, 'message': f'HTTP error occurred: {str(http_err)}'}), 500
    except Exception as e:
        app.logger.error(f'Error listing files: {str(e)}')
        return jsonify({'success': False, 'message': f'Error listing files: {str(e)}'}), 500

@app.route('/update_description', methods=['POST'], endpoint='update_description')
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
        app.logger.error(f'HTTP error occurred during description update: {str(http_err)}')
        return jsonify({'success': False, 'message': f'HTTP error occurred: {str(http_err)}'}), 500
    except Exception as e:
        app.logger.error(f'Error updating description: {str(e)}')
        return jsonify({'success': False, 'message': f'Error updating description: {str(e)}'}), 500

@app.route('/share_file', methods=['POST'], endpoint='share_file_route')
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
        app.logger.error(f'HTTP error occurred during file sharing: {str(http_err)}')
        return jsonify({'success': False, 'message': f'HTTP error occurred: {str(http_err)}'}), 500
    except Exception as e:
        app.logger.error(f'Error sharing file: {str(e)}')
        return jsonify({'success': False, 'message': f'Error sharing file: {str(e)}'}), 500

@app.route('/delete_file', methods=['POST'], endpoint='delete_file')
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
        app.logger.error(f'HTTP error occurred during file deletion: {str(http_err)}')
        return jsonify({'success': False, 'message': f'HTTP error occurred: {str(http_err)}'}), 500
    except Exception as e:
        app.logger.error(f'Error deleting file: {str(e)}')
        return jsonify({'success': False, 'message': f'Error deleting file: {str(e)}'}), 500

# if __name__ == '__main__':
#     app.run(debug=True)
