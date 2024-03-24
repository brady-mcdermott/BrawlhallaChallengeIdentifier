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
import json

config_file_name = 'app_config.ini'

if getattr(sys, 'frozen', False):
    # If the application is run as a bundle, the PyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app 
    # path into variable _MEIPASS'.
    application_path = sys._MEIPASS
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

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

class Challenge:
    def __init__(self, text, image_id):
        self.text = text
        self.completed = False
        self.image_id = image_id

class ChallengeManager:
    def __init__(self):
        self.challenges_by_image = {}
        self.load_challenges_from_file()

    def add_challenge(self, challenge_text, image_id):
        if image_id not in self.challenges_by_image:
            self.challenges_by_image[image_id] = []

        image_challenges = self.challenges_by_image[image_id]
        if challenge_text not in [c.text for c in image_challenges]:
            image_challenges.append(Challenge(challenge_text, image_id))

    def mark_completed(self, challenge_text, image_id, completed):
        for challenge in self.challenges_by_image.get(image_id, []):
            if challenge.text == challenge_text:
                challenge.completed = completed

    def get_active_challenges(self, image_id=None):
        active_challenges = []
        for src, challenges in self.challenges_by_image.items():
            if image_id is None or image_id == src:
                active_challenges.extend([c for c in challenges if not c.completed])
        return active_challenges
    
    def get_all_active_challenges(self):
        active_challenges = []
        for challenges in self.challenges_by_image.values():
            active_challenges.extend([c for c in challenges if not c.completed])
        return active_challenges
    
    def delete_challenge(self, image_id, challenge_text):
        for challenge in self.challenges_by_image[image_id]:
            if challenge.text == challenge_text:
                self.challenges_by_image[image_id].remove(challenge)
                if not self.challenges_by_image[image_id]:
                    del self.challenges_by_image[image_id]
                break
    
    def save_challenges_to_file(self, filename='challenges_info.json'):
        data = {image_id: [{'text': challenge.text, 'completed': challenge.completed} for challenge in challenges] for image_id, challenges in self.challenges_by_image.items()}
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)

    def load_challenges_from_file(self, filename='challenges_info.json'):
        try:
            with open(filename, 'r') as f:
                data_loaded = json.load(f)
                for image_id, challenges in data_loaded.items():
                    for challenge in challenges:
                        self.add_challenge(challenge['text'], image_id)
                        if challenge['completed']:
                            self.mark_completed(challenge['text'], image_id, True)
        except FileNotFoundError:
            pass

challenge_manager = ChallengeManager()


class AddChallengeDialog(wx.Dialog):
    def __init__(self, parent, title="Add Challenge"):
        super(AddChallengeDialog, self).__init__(parent, title=title, size=(300, 200))
        self.initUI()
        self.Centre()

    def initUI(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        self.challengeTextCtrl = wx.TextCtrl(panel)
        vbox.Add(wx.StaticText(panel, label="Challenge Title:"), flag=wx.LEFT | wx.TOP, border=10)
        vbox.Add(self.challengeTextCtrl, proportion=0, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=10)

        self.completedCheckBox = wx.CheckBox(panel, label="Completed")
        vbox.Add(self.completedCheckBox, flag=wx.LEFT | wx.TOP, border=10)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        okButton = wx.Button(panel, label='Ok', id=wx.ID_OK)
        cancelButton = wx.Button(panel, label='Cancel', id=wx.ID_CANCEL)
        hbox.Add(okButton)
        hbox.Add(cancelButton, flag=wx.LEFT, border=5)

        vbox.Add(hbox, flag=wx.ALIGN_CENTRE | wx.TOP | wx.BOTTOM, border=10)

        panel.SetSizer(vbox)

class ChallengesTab(wx.ScrolledWindow):
    def __init__(self, parent, challenge_manager, main_frame):
        super(ChallengesTab, self).__init__(parent)
        self.main_frame = main_frame
        self.challenge_manager = challenge_manager
        self.selectedChallengeText = None
        self.selectedChallengeImageId = None

        self.main_frame.updateIdentifiedChallenges()

        self.SetScrollRate(5, 5)
        self.initUI()

    def initUI(self):
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.lastSelectedChallenge = {}
        self.checkListDict = {}
        self.updateChallengesUI()

    def updateChallengesUI(self):

        self.sizer.Clear(True)

        challengesSizer = wx.BoxSizer(wx.VERTICAL)

        for image_id, challenges in sorted(self.challenge_manager.challenges_by_image.items()):
            label = wx.StaticText(self, label=f"Challenges from {image_id}")
            challengesSizer.Add(label, flag=wx.TOP | wx.LEFT | wx.RIGHT, border=10)
            challengesSizer.Add((-1, 10))

            # challenge_height = 20 * len(challenges)
            check_list_box = wx.CheckListBox(self, size=(-1, -1), choices=[c.text for c in challenges])
            self.checkListDict[image_id] = check_list_box
            challengesSizer.Add(check_list_box, flag=wx.EXPAND | wx.ALL, border=5)

            for index, challenge in enumerate(challenges):
                check_list_box.Check(index, challenge.completed)

            check_list_box.Bind(wx.EVT_LISTBOX, self.onSelectChallenge)
            check_list_box.Bind(wx.EVT_CHECKLISTBOX, lambda evt, id=image_id: self.onCheckChange(evt, id))

        self.sizer = challengesSizer
        self.SetSizer(challengesSizer)
        self.Layout()
        self.FitInside()

        self.challenge_manager.save_challenges_to_file()

    def onSelectChallenge(self, event):
        check_list_box = event.GetEventObject()
        if isinstance(check_list_box, wx.CheckListBox):
            selections = check_list_box.GetSelections()
            if selections:
                index = selections[0]
                for image_id, challenges in self.challenge_manager.challenges_by_image.items():
                    for challenge in challenges:
                        if check_list_box.GetString(index) == challenge.text:
                            self.selectedChallengeImageId = image_id
                            self.selectedChallengeText = challenge.text
                            break
                    if self.selectedChallengeImageId != None:
                        break

            else:
                self.selectedChallengeText = None
                self.selectedChallengeImageId = None
        event.Skip()

    def onCheckChange(self, event, image_id):
        self.lastSelectedChallenge[image_id] = event.GetSelection()

        check_list_box = self.checkListDict[image_id]
        checked_items = check_list_box.GetCheckedItems()
        challenges = self.challenge_manager.challenges_by_image[image_id]
        for index, challenge in enumerate(challenges):
            challenge.completed = index in checked_items
        
        
        self.main_frame.updateIdentifiedChallenges()

        self.challenge_manager.save_challenges_to_file()

    def onDeleteChallenge(self, event):
        # Check if an image ID and challenge index has been selected
        if self.selectedChallengeImageId is not None and self.selectedChallengeText is not None:
            print(self.selectedChallengeImageId + "\n" + self.selectedChallengeText)
            # Call the delete_challenge method from ChallengeManager
            self.challenge_manager.delete_challenge(self.selectedChallengeImageId, self.selectedChallengeText)
            # Update the UI after deletion
            self.rebuildCheckListBox(self.selectedChallengeImageId)
            self.updateChallengesUI()
            # Reset the selected index and image ID
            self.selectedChallengeText = None
            self.selectedChallengeImageId = None
            self.main_frame.updateIdentifiedChallenges()

    def rebuildCheckListBox(self, image_id):
        old_check_list_box = self.checkListDict.get(image_id)
        clb_sizer_index = None

        for i in range(self.sizer.GetItemCount()):
            item = self.sizer.GetItem(i)
            widget = item.GetWindow()
            if widget == old_check_list_box:
                clb_sizer_index = i
                self.sizer.Detach(widget)
                widget.Destroy()
                break

        new_challenges = [c.text for c in self.challenge_manager.challenges_by_image.get(image_id, [])]
        new_check_list_box = wx.CheckListBox(self, size=(-1, -1), choices=new_challenges)
        self.checkListDict[image_id] = new_check_list_box

        for index, challenge in enumerate(self.challenge_manager.challenges_by_image.get(image_id, [])):
            new_check_list_box.Check(index, challenge.completed)

        new_check_list_box.Bind(wx.EVT_LISTBOX, self.onSelectChallenge)
        new_check_list_box.Bind(wx.EVT_CHECKLISTBOX, lambda evt, id=image_id: self.onCheckChange(evt, id))

        if clb_sizer_index is not None:
            self.sizer.Insert(clb_sizer_index, new_check_list_box, flag=wx.EXPAND | wx.ALL, border=5)
            self.Layout()
            self.FitInside()


    def getChallengeTexts(self):
        challenge_texts_with_labels = []
        for image_id, challenges in self.challenge_manager.challenges_by_image.items():
            challenge_texts_with_labels.append(f"Challenges from {image_id}")
            challenge_texts_with_labels.extend([c.text for c in challenges])
        return challenge_texts_with_labels
    
    def onAddChallenge(self, event):
        dlg = AddChallengeDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            challenge_text = dlg.challengeTextCtrl.GetValue()
            completed = dlg.completedCheckBox.IsChecked()
            challenge_id = "Added Challenges"


            self.challenge_manager.add_challenge(challenge_text, challenge_id)
            self.challenge_manager.mark_completed(challenge_text, challenge_id, completed)

            self.updateChallengesUI()
            self.main_frame.updateIdentifiedChallenges()
            self.challenge_manager.save_challenges_to_file()
        dlg.Destroy()

class MainFrame(wx.Frame):
    def __init__(self, parent, id, title, size, challenge_manager):
        super(MainFrame, self).__init__(parent, id, title)
        self.challenge_manager = challenge_manager
        self.SetSize(size)
        self.InitUI()

        self.challenge_manager.load_challenges_from_file()

    def InitUI(self):

        self.panel = wx.Panel(self)
        mainSizer = wx.BoxSizer(wx.VERTICAL)

        self.actionButtonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.notebookSizer = wx.BoxSizer(wx.VERTICAL)

        self.openButton = wx.Button(self.panel, label='Open Image')
        self.identifyButton = wx.Button(self.panel, label='Identify')
        self.identifyButton.Disable()  # Disable until images are uploaded

        self.addButton = wx.Button(self.panel, label="Add Challenge")
        self.deleteButton = wx.Button(self.panel, label="Delete Challenge")

        self.actionButtonSizer.Add(self.openButton, 0, wx.ALL, 5)
        self.actionButtonSizer.Add(self.identifyButton, 0, wx.ALL, 5)

        self.openButton.Bind(wx.EVT_BUTTON, self.onOpenImage)
        self.identifyButton.Bind(wx.EVT_BUTTON, self.onIdentifyChallenges)

        self.notebook = wx.Notebook(self.panel)
        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnTabChanged)

        self.identifiedChallengesTab = wx.Panel(self.notebook)
        identifiedChallengesSizer = wx.BoxSizer(wx.VERTICAL)
        self.imageTitlesText = wx.TextCtrl(self.identifiedChallengesTab, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.resultText = wx.TextCtrl(self.identifiedChallengesTab, style=wx.TE_MULTILINE)
        identifiedChallengesSizer.Add(self.imageTitlesText, 0, wx.EXPAND | wx.ALL, 5)
        identifiedChallengesSizer.Add(self.resultText, 1, wx.EXPAND | wx.ALL, 5)
        self.identifiedChallengesTab.SetSizer(identifiedChallengesSizer)
        self.notebook.AddPage(self.identifiedChallengesTab, "Identified Challenges")

        self.challengesTab = ChallengesTab(self.notebook, challenge_manager=challenge_manager, main_frame=self)
        self.notebook.AddPage(self.challengesTab, "Challenges")
        
        self.addButton.Bind(wx.EVT_BUTTON, self.challengesTab.onAddChallenge)
        self.deleteButton.Bind(wx.EVT_BUTTON, self.challengesTab.onDeleteChallenge)

        self.addButton.Hide()
        self.deleteButton.Hide()

        self.notebookSizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)

        mainSizer.Add(self.actionButtonSizer, 0, wx.EXPAND)
        mainSizer.Add(self.notebookSizer, 1, wx.EXPAND | wx.ALL)

        self.panel.SetSizer(mainSizer)
        self.Layout()

        self.imagePaths = []  # Store uploaded image paths

    def OnTabChanged(self, event):
        # Show or hide action buttons based on the selected tab
        if isinstance(self.notebook.GetCurrentPage(), ChallengesTab):
            self.openButton.Hide()
            self.identifyButton.Hide()
            self.actionButtonSizer.Detach(self.openButton)
            self.actionButtonSizer.Detach(self.identifyButton)
            self.actionButtonSizer.Add(self.addButton, 0, wx.ALL, 5)
            self.actionButtonSizer.Add(self.deleteButton, 0, wx.ALL, 5)
            self.addButton.Show()
            self.deleteButton.Show()
        else:
            self.addButton.Hide()
            self.deleteButton.Hide()
            self.actionButtonSizer.Detach(self.addButton)
            self.actionButtonSizer.Detach(self.deleteButton)
            self.actionButtonSizer.Add(self.openButton, 0, wx.ALL, 5)
            self.actionButtonSizer.Add(self.identifyButton, 0, wx.ALL, 5)
            self.openButton.Show()
            self.identifyButton.Show()

        self.actionButtonSizer.Layout()
        self.panel.Layout()
        event.Skip()

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
            challenges = self.identify_challenges(text, imagePath)
            all_challenges.extend(challenges)

        all_challenges = list(dict.fromkeys(all_challenges))  # Remove duplicates
        best_characters, challenges_per_character = self.find_best_characters_for_challenges(all_challenges, self.get_character_traits())

        self.challengesTab.updateChallengesUI()

        # Generate display text
        display_text = ""
        for character in best_characters:
            display_text += f"Best character: {character}\nChallenges:\n"
            for challenge in challenges_per_character[character]:
                display_text += f"- {challenge}\n"
            display_text += "\n"  # Add extra newline for spacing between characters

        self.resultText.SetValue(display_text)

        self.challenge_manager.save_challenges_to_file()

    def updateIdentifiedChallenges(self):
        all_challenges = self.challenge_manager.get_all_active_challenges()
        if not all_challenges:
            self.resultText.SetValue("No challenges identified")
            return

        best_characters, challenges_per_character = self.find_best_characters_for_challenges(all_challenges, self.get_character_traits())

        # Generate display text
        display_text = ""
        for character in best_characters:
            if character == "No matching characters for the challenges":
                display_text = character
                break
            display_text += f"Best character: {character}\nChallenges:\n"
            for challenge in challenges_per_character[character]:
                display_text += f"- {challenge}\n"
            display_text += "\n"  # Add extra newline for spacing between characters

        self.resultText.SetValue(display_text)

    def processImages(self, imagePaths):
        all_challenges = []
        for imagePath in imagePaths:
            text = self.extractTextFromImage(imagePath)
            challenges = self.identify_challenges(text, imagePath)
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

    def identify_challenges(self, text, image_id):

        completed_challenges = re.findall(r'\b(Completed|completed|Compieted)\b\s*(.*?)\n', text)

        for _, challenge_text in completed_challenges:
            challenge_text = challenge_text.strip()
            if challenge_text:
                challenge_manager.add_challenge(challenge_text, image_id)
                challenge_manager.mark_completed(challenge_text, image_id, True)

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
                    challenge_manager.add_challenge(primary_part, image_id)

        # Remove duplicates while preserving order
        deduped_challenges = list(dict.fromkeys(extracted_challenges))
        return deduped_challenges

    def find_best_characters_for_challenges(self, challenges, character_traits):
        
        active_challenges = [challenge.text for challenge in challenge_manager.get_active_challenges()]
        
        if not active_challenges:
            return ["No specific challenges identified"], {}

        challenge_coverage = {character: [] for character in character_traits}  # Tracks challenges per character
        for challenge in active_challenges:
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
    frame = MainFrame(None, -1, 'Brawlhalla Challenge Extractor', size=(800, 400), challenge_manager=challenge_manager)
    frame.Show(True)

    set_tesseract_path(frame)
    app.MainLoop()

if __name__ == '__main__':
    main()