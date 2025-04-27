// viewer-button.ts
export class ViewerButton {
  private buttonElement: HTMLButtonElement;
  private statusElement: HTMLDivElement;
  private apiUrl: string;

  constructor(containerId: string, apiUrl: string = "http://localhost:5000") {
    const container = document.getElementById(containerId);
    if (!container)
      throw new Error(`Container with ID ${containerId} not found`);

    this.apiUrl = apiUrl;

    // Create button
    this.buttonElement = document.createElement("button");
    this.buttonElement.textContent = "Launch DICOM Viewer";
    this.buttonElement.className = "viewer-button";
    this.buttonElement.addEventListener("click", this.handleClick.bind(this));

    // Create status display
    this.statusElement = document.createElement("div");
    this.statusElement.className = "viewer-status";

    // Add elements to container
    container.appendChild(this.buttonElement);
    container.appendChild(this.statusElement);
  }

  private async handleClick() {
    try {
      this.setStatus("Launching DICOM Viewer...");
      this.buttonElement.disabled = true;

      const response = await fetch(`${this.apiUrl}/run-viewer`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ scanDir: "scan" }), // You can make this configurable
      });

      const data = await response.json();

      if (data.success) {
        this.setStatus(
          "DICOM Viewer launched successfully! Check your desktop for the application window."
        );
      } else {
        this.setStatus(`Error: ${data.error || "Unknown error"}`);
      }
    } catch (error: unknown) {
      // Properly type the error
      let errorMessage = "Unknown error occurred";

      if (error instanceof Error) {
        errorMessage = error.message;
      } else if (typeof error === "string") {
        errorMessage = error;
      } else if (error && typeof error === "object" && "message" in error) {
        errorMessage = String(error.message);
      }

      this.setStatus(`Failed to communicate with server: ${errorMessage}`);
      console.error(error);
    } finally {
      setTimeout(() => {
        this.buttonElement.disabled = false;
      }, 2000); // Short delay to prevent multiple clicks
    }
  }

  private setStatus(message: string) {
    this.statusElement.textContent = message;
  }
}
