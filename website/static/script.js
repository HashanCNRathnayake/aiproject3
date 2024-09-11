function deleteNote(noteId) {
  fetch("/delete-note", {
    method: "POST",
    body: JSON.stringify({ noteId: noteId }),
  }).then((_res) => {
    window.location.href = "/note";
  });
}

// Function to handle the upload form submission
document
  .getElementById("upload-form")
  .addEventListener("submit", function (event) {
    event.preventDefault();

    const fileInput = document.getElementById("file-input");
    const file = fileInput.files[0];
    const descriptionInput = document.getElementById("description-input");
    const description = descriptionInput.value;
    const folderInput = document.getElementById("folder-input");
    const folder = folderInput.value;

    if (!file) {
      showNotification("error", "Please select a file first.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("description", description);
    formData.append("folder", folder);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/upload", true);

    xhr.upload.addEventListener("progress", function (event) {
      if (event.lengthComputable) {
        const percentComplete = (event.loaded / event.total) * 100;
        document.getElementById("progress-bar").value = percentComplete;
        document.getElementById(
          "progress-message"
        ).textContent = `Upload Progress: ${Math.round(percentComplete)}%`;
      }
    });

    xhr.onload = function () {
      if (xhr.status === 200) {
        const response = JSON.parse(xhr.responseText);
        if (response.success) {
          document.getElementById("progress-message").textContent =
            "File uploaded successfully!";
          const fileDetails = {
            id: response.file_id,
            name: response.file_name,
            description: description,
            owner: response.owner,
            uploaded_date: response.uploaded_date,
          };
          addFileToList(fileDetails);
        } else {
          document.getElementById("progress-message").textContent =
            "Upload failed: " + response.message;
        }
      } else {
        document.getElementById("progress-message").textContent =
          "Upload failed with status: " + xhr.status;
      }
    };

    xhr.onerror = function () {
      document.getElementById("progress-message").textContent =
        "An error occurred during the file upload.";
    };

    xhr.send(formData);
  });

// Function to add a file to the top of the file list
function addFileToList(file) {
  const fileItemsContainer = document.getElementById("file-items-container");

  const fileItem = document.createElement("div");
  fileItem.className = "file-item";
  fileItem.setAttribute("data-file-id", file.id);
  fileItem.innerHTML = `
      <span class="truncate">
          <a href="https://drive.google.com/file/d/${
            file.id
          }/view" target="_blank" class="text-gray-400 hover:text-white">
              ${file.name}
          </a>
      </span>
      <span class="truncate">${file.owner}</span>
      <span class="truncate">${file.uploaded_date}</span>
      <span class="truncate description">${
        file.description || "No description"
      }</span>
      <span class="flex justify-center">
          <button onclick="showOptionsMenu('${file.id}', '${
    file.description || ""
  }')" class="text-gray-400 hover:text-white">
              <svg class="w-6 h-6 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
              </svg>
          </button>
      </span>
  `;

  fileItemsContainer.insertBefore(fileItem, fileItemsContainer.firstChild);
}

// Function to fetch files and update the file list
function fetchFiles() {
  fetch("/list_files")
    .then((response) => response.json())
    .then((data) => {
      const fileItemsContainer = document.getElementById(
        "file-items-container"
      );
      fileItemsContainer.innerHTML = "";
      data.forEach((file) => addFileToList(file));
    })
    .catch((error) => {
      console.error("Error:", error);
      showNotification("error", "An error occurred while fetching files.");
    });
}

// Function to display the options menu
function showOptionsMenu(fileId, currentDescription) {
  const menuHtml = `
      <div class="fixed inset-0 flex items-center justify-center bg-gray-800 bg-opacity-75 z-50">
          <div class="bg-gray-900 p-6 rounded-lg shadow-lg w-80">
              <h2 class="text-xl font-bold mb-4">File Options</h2>
              <button onclick="addDescription('${fileId}')" class="block w-full text-left px-4 py-2 text-blue-600 hover:bg-blue-800 rounded mb-2">Add smart search tag</button>
              <button onclick="editDescription('${fileId}', '${currentDescription}')" class="block w-full text-left px-4 py-2 text-blue-600 hover:bg-blue-800 rounded mb-2">Edit smart search tag</button>
              <button onclick="shareFile('${fileId}')" class="block w-full text-left px-4 py-2 text-blue-600 hover:bg-blue-800 rounded mb-2">Share</button>
              <button onclick="deleteFile('${fileId}')" class="block w-full text-left px-4 py-2 text-red-600 hover:bg-red-800 rounded mb-2">Delete</button>
              <button onclick="analyzeFile('${fileId}')" class="block w-full text-left px-4 py-2 text-green-600 hover:bg-green-800 rounded mb-2">Analyze with AI</button>
              <button onclick="closeOptionsMenu()" class="block w-full text-left px-4 py-2 text-gray-600 hover:bg-gray-800 rounded">Cancel</button>
          </div>
      </div>
  `;
  document.getElementById("options-menu-container").innerHTML = menuHtml;
}

// Function to share the file
function shareFile(fileId) {
  fetch("/share_file", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ fileId: fileId }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        alert(
          `File shared successfully! You can view it here: ${data.viewLink}`
        );
        updateFileSharingStatus(fileId, "Shared");
      } else {
        alert(data.message);
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("Failed to share file.");
    });

  closeOptionsMenu();
}

// Function to update the file sharing status in the UI
function updateFileSharingStatus(fileId, status) {
  const fileElement = document.querySelector(`[data-file-id="${fileId}"]`);
  if (fileElement) {
    const statusElement = fileElement.querySelector(".sharing-status");
    if (statusElement) {
      statusElement.textContent = status;
    }
  }
}

// Function to delete the file
function deleteFile(fileId) {
  fetch("/delete_file", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ fileId: fileId }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        alert(data.message);
        removeFileFromUI(fileId);
      } else {
        alert(data.message);
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("Failed to delete file.");
    });

  closeOptionsMenu();
}

// Function to remove file from the UI
function removeFileFromUI(fileId) {
  const fileElement = document.querySelector(`[data-file-id="${fileId}"]`);
  if (fileElement) {
    fileElement.remove();
  }
}

// Function to analyze the file with AI
function analyzeFile(fileId) {
  // Placeholder for future AI analysis feature
  alert(`Analyze file with ID: ${fileId}`);
  closeOptionsMenu();
}

// Function to close the options menu
function closeOptionsMenu() {
  document.getElementById("options-menu-container").innerHTML = "";
}

// Function to prompt for description and add it
function addDescription(fileId) {
  const description = prompt("Enter description:");
  if (description) {
    updateDescription(fileId, description);
  } else {
    closeOptionsMenu();
  }
}

// Function to prompt for description editing
function editDescription(fileId, currentDescription) {
  const description = prompt("Edit description:", currentDescription);
  if (description !== null) {
    updateDescription(fileId, description);
  } else {
    closeOptionsMenu();
  }
}

// Function to update the file description
function updateDescription(fileId, description) {
  console.log(
    `Updating description for fileId: ${fileId}, new description: ${description}`
  );

  fetch("/update_description", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ fileId: fileId, description: description }),
  })
    .then((response) => response.json())
    .then((data) => {
      console.log("Server response:", data);
      if (data.success) {
        alert("Description updated successfully.");
        const descriptionElement = document.querySelector(
          `[data-file-id="${fileId}"] .description`
        );
        if (descriptionElement) {
          descriptionElement.textContent = description;
        } else {
          console.error(`No element found for fileId: ${fileId}`);
        }
      } else {
        console.error("Server error:", data.message); // Log server error to the console
        alert(data.message); // Alert with server error message
      }
    })
    .catch((error) => {
      console.error("Network error:", error); // Log network error to the console
      alert("Failed to update description."); // Alert for network errors
    });

  closeOptionsMenu();
}

// Initialize file list on page load
document.addEventListener("DOMContentLoaded", function () {
  fetchFiles();
});
