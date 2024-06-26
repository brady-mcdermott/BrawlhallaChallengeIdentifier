# Brawlhalla Challenge Identifier

The Brawlhalla Challenge Identifier is a desktop application designed to help players identify the best characters to complete specific challenges in the game Brawlhalla. It uses OCR (Optical Character Recognition) to extract challenge descriptions from screenshots and recommends characters based on their abilities to meet these challenges.

## Features

- Extract challenge descriptions from images using OCR.
- Identify the best Brawlhalla characters for completing these challenges.
- User-friendly GUI for easy operation.
- Ability to manually set the path to the Tesseract OCR engine.
- Packaged as an executable for easy distribution and use without needing Python installed.
- **New:** Manually add challenges and mark them as completed.
- **New:** Save and load challenges across sessions, keeping track of progress without needing to re-upload images.
- **New:** Improved GUI with a new section for manually added challenges.

## Prerequisites

Before you begin, ensure you have met the following requirements:

- Python 3.6 or later is installed on your machine if you wish to run the script directly.
- Tesseract OCR is installed and accessible in your system's PATH or in the default installation directory. Tesseract OCR can be downloaded from [here](https://github.com/tesseract-ocr/tesseract).

## Installation and Usage

### Running from Source

1. Clone the repository to your local machine:

```bash
git clone https://github.com/yourusername/brawlhalla-challenge-Identifier.git
cd brawlhalla-challenge-Identifier
```

2. Install the required Python packages:

```bash
pip install -r requirements.txt
```

The `requirements.txt` file should include at least:
- `wxPython`
- `pytesseract`
- `Pillow`
- `opencv-python`
- `ftfy`

3. Ensure Tesseract OCR is correctly installed. If the application does not automatically detect Tesseract OCR, it will prompt you to select the installation directory manually.

4. To start the application, run:

```bash
python main.py
```

### Using the Executable

If you prefer not to run the script directly or do not have Python installed, you can find an executable file in the `dist` folder.

## Usage

After running the application you will be prompted to upload screenshots of the current week's challenges. You **may** upload multiple images at one time.

### Example Challenge Screenshot

Below is an example of a Brawlhalla challenge screenshot that the application can process:

<img src="images/week1.png" alt="Week 1 Challenges Image" width="600">

This screenshot demonstrates the kind of image you should upload to the Brawlhalla Challenge Identifier to identify the best characters for completing these challenges.

## Contributing

Contributions to the Brawlhalla Challenge Identifier are welcome. Please ensure to update tests as appropriate.

## Updates
- **Added Manual Challenge Addition**: Users can now manually add challenges through a simple dialog interface, marking them as completed if necessary. These are listed under "Added Challenges" in the GUI.
- **Persistent Challenge Data**: The application now saves challenge data (both from OCR and manually added) to a file, allowing users to retain their progress between sessions.
- **GUI Enhancements**: Updated the user interface for better usability and integration of new features, including a distinct section for "Added Challenges."

## License

This project is licensed under the [MIT License](LICENSE).
