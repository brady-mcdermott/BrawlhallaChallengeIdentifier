import wx
import pytesseract
from PIL import Image, ImageFilter, ImageOps, ImageEnhance
import re
import cv2
import os
import sys
import uuid
import ftfy
import string
import configparser

config_file_name = 'app_config.ini'

class TesseractPathFrame(wx.Frame):
    def __init__(self, parent, title):
        super(TesseractPathFrame, self).__init__(parent, title=title, size=(400, 150))
        self.InitUI()
        self.Centre()
        self.Show()

    def InitUI(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        msg = "Tesseract executable not found, please select the installation folder:"
        label = wx.StaticText(panel, label=msg)
        vbox.Add(label, flag=wx.ALL | wx.EXPAND, border=10)

        self.path_text_ctrl = wx.TextCtrl(panel)
        vbox.Add(self.path_text_ctrl, proportion=1, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=10)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        browse_button = wx.Button(panel, label='Browse...')
        browse_button.Bind(wx.EVT_BUTTON, self.OnBrowse)
        hbox.Add(browse_button)

        done_button = wx.Button(panel, label='Done')
        done_button.Bind(wx.EVT_BUTTON, self.OnDone)
        hbox.Add(done_button, flag=wx.LEFT, border=10)

        vbox.Add(hbox, flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, border=10)

        panel.SetSizer(vbox)

    def OnBrowse(self, event):
        dialog = wx.DirDialog(self, "Select the Tesseract-OCR installation folder:",
                            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dialog.ShowModal() == wx.ID_OK:
            self.path_text_ctrl.SetValue(dialog.GetPath())
        dialog.Destroy()

    def OnDone(self, event):
        tesseract_path = self.path_text_ctrl.GetValue()
        tesseract_executable_path = os.path.join(tesseract_path, 'tesseract.exe')
        if os.path.isfile(tesseract_executable_path):
            save_tesseract_path(tesseract_executable_path)
            pytesseract.pytesseract.tesseract_cmd = tesseract_executable_path
            self.Close()
        else:
            wx.MessageBox('Tesseract executable not found in the provided directory. Please try again.', 'Error', wx.OK | wx.ICON_ERROR)

def save_tesseract_path(path):
    config = configparser.ConfigParser()
    config['Tesseract-OCR'] = {'Path': path}
    with open(config_file_name, 'w') as configfile:
        config.write(configfile)

def load_tesseract_path():
    if not os.path.exists(config_file_name):
        return None
    config = configparser.ConfigParser()
    config.read(config_file_name)
    try:
        return config['Tesseract-OCR']['Path']
    except KeyError:
        return None

def set_tesseract_path(parent_frame):
    # Check the generic installation path first
    generic_path = r'C:/Program Files/Tesseract-OCR/tesseract.exe'
    if os.path.isfile(generic_path):
        pytesseract.pytesseract.tesseract_cmd = generic_path
        save_tesseract_path(generic_path)  # Save this path for future use
        return
    
    # If not found, try loading the saved path
    saved_path = load_tesseract_path()
    if saved_path and os.path.isfile(saved_path):
        pytesseract.pytesseract.tesseract_cmd = saved_path
    else:
        # If still not found, prompt the user with the custom frame
        TesseractPathFrame(parent_frame, "Set Tesseract Path")

class MainFrame(wx.Frame):
    def __init__(self, parent, id, title, size):
        super(MainFrame, self).__init__(parent, id, title)
        self.SetSize(size)
        self.InitUI()

    def InitUI(self):
        self.panel = wx.Panel(self)
        self.openButton = wx.Button(self.panel, label='Open Image', pos=(10, 10))
        self.identifyButton = wx.Button(self.panel, label='Identify', pos=(120, 10))
        self.identifyButton.Disable()  # Disable until images are uploaded

        # Multi-line TextCtrl for displaying image titles
        self.imageTitlesText = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE | wx.TE_READONLY, pos=(230, 10), size=(150, 90))

        self.resultText = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE, pos=(10, 110), size=(780, 280))

        self.openButton.Bind(wx.EVT_BUTTON, self.onOpenImage)
        self.identifyButton.Bind(wx.EVT_BUTTON, self.onIdentifyChallenges)

        self.imagePaths = []  # Store uploaded image paths

    def onOpenImage(self, event):
        with wx.FileDialog(self, "Open Image file", wildcard="Image files (*.png;*.jpeg;*.jpg)|*.png;*.jpeg;*.jpg",
                        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return  # User cancelled the dialog
            # Get multiple selected file paths
            newImagePaths = fileDialog.GetPaths()
            self.imagePaths.extend(newImagePaths)
            self.identifyButton.Enable()  # Enable the Identify button after uploading

            # Update the list with each uploaded image title, truncating if necessary
            for imagePath in newImagePaths:
                title = os.path.splitext(os.path.basename(imagePath))[0]
                displayTitle = (title[:10] + '...') if len(title) > 10 else title
                currentTitles = self.imageTitlesText.GetValue()
                self.imageTitlesText.SetValue(currentTitles + displayTitle + '\n')

    def onIdentifyChallenges(self, event):
        if not self.imagePaths:
            wx.MessageBox("No images uploaded.", "Error", wx.OK | wx.ICON_ERROR)
            return

        all_challenges = []
        for imagePath in self.imagePaths:
            text = self.extractTextFromImage(imagePath)
            challenges = self.identify_challenges(text)
            all_challenges.extend(challenges)

        all_challenges = list(dict.fromkeys(all_challenges))  # Remove duplicates
        best_characters, challenges_per_character = self.find_best_characters_for_challenges(all_challenges, self.get_character_traits())

        # Generate display text
        display_text = ""
        for character in best_characters:
            display_text += f"Best character: {character}\nChallenges:\n"
            for challenge in challenges_per_character[character]:
                display_text += f"- {challenge}\n"
            display_text += "\n"  # Add extra newline for spacing between characters

        self.resultText.SetValue(display_text)

    def processImages(self, imagePaths):
        all_challenges = []
        for imagePath in imagePaths:
            text = self.extractTextFromImage(imagePath)
            challenges = self.identify_challenges(text)
            all_challenges.extend(challenges)
        # Remove duplicates while preserving order
        all_challenges = list(dict.fromkeys(all_challenges))
        print("Identified Challenges from all images:", all_challenges)  # Debug print statement
        best_characters = self.find_best_characters_for_challenges(all_challenges, self.get_character_traits())
        self.resultText.SetValue("Best character(s) to complete the challenges: " + ", ".join(best_characters))

    def extractTextFromImage(self, imagePath):
        image = cv2.imread(imagePath)
        gray = cv2.threshold(image, 200, 255, cv2.THRESH_BINARY)[1]
        gray = cv2.resize(gray, (0, 0), fx=3, fy=3)
        gray = cv2.medianBlur(gray, 9)
        filename = str(uuid.uuid4())+".jpg"
        cv2.imwrite(os.path.join(filename), gray)
        config = ("-l eng --oem 3 --psm 11")
        text = pytesseract.image_to_string(Image.open(os.path.join(filename)), config=config)
        text = ftfy.fix_text(text)
        text = ftfy.fix_encoding(text)
        os.remove(os.path.join(filename))  # Clean up the temporary file
        return text

    def identify_challenges(self, text):
        # Normalize the text to replace known completion markers with a newline
        text = re.sub(r'\b(Compieted|completed|Completed)\b', '\n', text)
        # Use progress markers as cues to split challenges
        text = re.sub(r'(\d+/\d+)', r'\n', text)

        # Split the text into potential challenges based on the updated delimiters
        potential_challenges = text.split('\n')

        extracted_challenges = []
        for challenge in potential_challenges:
            # Clean up each challenge string
            challenge = challenge.strip()
            # Exclude short fragments that are unlikely to be valid challenges
            if len(challenge) > 3 and not all(char in string.punctuation for char in challenge):
                # Check if challenge ends with a progress marker, if so, split and take the first part
                parts = re.split(r'(\d+/\d+)', challenge)
                primary_part = parts[0].strip()
                if primary_part:
                    extracted_challenges.append(primary_part)

        # Remove duplicates while preserving order
        deduped_challenges = list(dict.fromkeys(extracted_challenges))
        return deduped_challenges

    def find_best_characters_for_challenges(self, challenges, character_traits):
        if not challenges:
            return ["No specific challenges identified"], {}

        challenge_coverage = {character: [] for character in character_traits}  # Tracks challenges per character
        for challenge in challenges:
            for character, traits in character_traits.items():
                if any(trait in challenge for trait in traits):
                    challenge_coverage[character].append(challenge)

        # Filter out characters with no challenges matched
        challenge_coverage = {k: v for k, v in challenge_coverage.items() if v}

        if not challenge_coverage:
            return ["No matching characters for the challenges"], {}

        # Find characters with the maximum number of challenges matched
        max_challenges = max(len(challenges) for challenges in challenge_coverage.values())
        best_characters = {character: challenges for character, challenges in challenge_coverage.items() if len(challenges) == max_challenges}

        return list(best_characters.keys()), best_characters

    def get_character_traits(self):
        return {
            "Bodvar": ["Hammer", "Sword"],
            "Cassidy": ["Hammer", "Blasters"],
            "Orion": ["Spear", "Rocket Lance"],
            "Lord Vraxx": ["Rocket Lance", "Blasters"],
            "Gnash": ["Hammer", "Spear"],
            "Queen Nai": ["Spear", "Katars"],
            "Hattori": ["Sword", "Spear"],
            "Sir Roland": ["Sword", "Rocket Lance"],
            "Scarlet": ["Hammer", "Rocket Lance"],
            "Thatch": ["Sword", "Blasters"],
            "Ada": ["Spear", "Blasters"],
            "Sentinel": ["Katars", "Hammer"],
            "Lucien": ["Katars", "Blasters"],
            "Teros": ["Axe", "Hammer"],
            "Brynn": ["Axe", "Spear"],
            "Asuri": ["Sword", "Katars"],
            "Barraza": ["Axe", "Blasters"],
            "Ember": ["Bow", "Katars"],
            "Azoth": ["Bow", "Axe"],
            "Koji": ["Bow", "Sword"],
            "Ulgrim": ["Axe", "Rocket Lance"],
            "Diana": ["Bow", "Blasters"],
            "Jhala": ["Sword", "Axe"],
            "Kor": ["Gauntlets", "Hammer"],
            "Wu Shang": ["Spear", "Gauntlets"],
            "Val": ["Sword", "Gauntlets"],
            "Ragnir": ["Axe", "Katars"],
            "Cross": ["Blasters", "Gauntlets"],
            "Mirage": ["Spear", "Scythe"],
            "Nix": ["Blasters", "Scythe"],
            "Mordex": ["Gauntlets", "Scythe"],
            "Yumiko": ["Hammer", "Bow"],
            "Artemis": ["Rocket Lance", "Scythe"],
            "Caspian": ["Gauntlets", "Katars"],
            "Sidra": ["Cannon", "Sword"],
            "Xull": ["Cannon", "Axe"],
            "Kaya": ["Spear", "Bow"],
            "Isaiah": ["Cannon", "Blasters"],
            "Jiro": ["Sword", "Scythe"],
            "Lin Fei": ["Katars", "Cannon"],
            "Zariel": ["Gauntlets", "Bow"],
            "Rayman": ["Axe", "Gauntlets"],
            "Dusk": ["Orb", "Spear"],
            "Fait": ["Orb", "Scythe"],
            "Thor": ["Orb", "Hammer"],
            "Petra": ["Gauntlets", "Orb"],
            "Vector": ["Bow", "Rocket Lance"],
            "Volkov": ["Scythe", "Axe"],
            "Onyx": ["Cannon", "Gauntlets"],
            "Jaeyun": ["Sword", "Greatsword"],
            "Mako": ["Katars", "Greatsword"],
            "Magyar": ["Hammer", "Greatsword"],
            "Reno": ["Blasters", "Orb"],
            "Munin" : ["Scythe", "Bow"],
            "Arcadia" : ["Greatsword", "Spear"],
            "Ezio" : ["Sword", "Orb"],
            "Tezca" : ["Battle Boots", "Gauntlets"],
            "Thea" : ["Rocket Lance", "Battle Boots"],
            "Red Raptor" : ["Battle Boots", "Orb"],
            "Loki" : ["Scythe", "Katars"],
            "Seven" : ["Cannon", "Spear"]
        }

def main():
    app = wx.App(False)
    frame = MainFrame(None, -1, 'Brawlhalla Challenge Extractor', size=(800, 400))
    frame.Show(True)

    set_tesseract_path(frame)
    app.MainLoop()

if __name__ == '__main__':
    main()