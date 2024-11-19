""" This module handles everything related to log parsing """
import re       # For parsing the log file (regular expressions)
import os       # For working with files on the operating system
import logging  # For logging
import shutil   # For backing logs
from datetime import datetime
from game_objects.item import Item
from game_objects.floor import Floor, Curse
from game_objects.state import TrackerState
from options import Options
from view_controls.view import DrawingTool
from error_stuff import log_error

class LogParser(object):
    """
    This class loads Isaac's log file, and incrementally modify a state representing this log
    """
    def __init__(self, prefix, tracker_version, log_finder):
        self.state = TrackerState("", tracker_version, Options().game_version, "", "", "", "", -1)
        self.log = logging.getLogger("tracker")
        self.wdir_prefix = prefix
        self.log_finder = log_finder

        self.reset()

    def reset(self):
        """Reset variable specific to the log file/run"""
        # Variables describing the parser state
        self.getting_start_items = False
        self.reseeding_floor = False
        self.current_seed = ""
        # Cached contents of log
        self.content = ""
        # Log split into lines
        self.splitfile = []
        self.run_start_line = 0
        self.seek = 0
        self.spawned_coop_baby = 0
        self.log_file_handle = None
        # if they switched between rebirth and afterbirth, the log file we use could change
        self.log_file_path = self.log_finder.find_log_file(self.wdir_prefix)
        self.state.reset(self.current_seed, Options().game_version, "", "", "")
        self.greed_mode_starting_rooms = ('1.1000','1.1010','1.1011','1.1012','1.1013','1.1014','1.1015','1.1016','1.1017','1.1018','1.2000','1.2001','1.2002','1.2003','1.2004','1.2005','1.2006','1.2007','1.2008','1.2009','1.3000','1.3001','1.3002','1.3003','1.3004','1.3005','1.3006','1.3007','1.3008','1.3009','1.3010','1.4000','1.4001','1.4002','1.4003','1.4004','1.4005','1.4006','1.4007','1.4008','1.4009','1.4010','1.5000','1.5001','1.5002','1.5003','1.5004','1.5005','1.5006','1.5007','1.5008','1.5009','1.5010','1.6000','1.6001','1.6002','1.6003','1.6004','1.6005','1.6006','1.6007','1.6008','1.6009')
        self.first_floor = None
        self.first_line = ""
        self.curse_first_floor = ""
        self.is_online_run = False
        
        self.jacob_names = ("(Jacob)", "(Иаков)", "(雅各)", "(ヤコブ)", "(Jakob)", "(야곱)")
        self.esau_names = ("(Esau)", "(Ésaü)", "(Исав)", "(以扫)", "(エサウ)", "(Esaú)", "(에사우)")
        self.esau1_names = (" 1 (Esau)", " 1 (Ésaü)", " 1 (Исав)", " 1 (以扫)", " 1 (エサウ)", " 1 (Esaú)", " 1 (에사우)")
        self.keeper_names = ("(Keeper)", "(Le Gardien)", "(Хранитель)", "(店主)", "(キーパー)", "(Hüter)", "(키퍼)")
        self.double_words_chars = ("(The Lost)", "(The Forgotten)", "(The Soul)", "(Black Judas)", "(Random Baby)", "(The Deleted)", "(The Stranger)", "(Le Gardien)", "(Le Délaissé)", "(Темный Иуда)", "(ダーク ユダ)", "(ザ フォーガットン)", "(ザ ソウル)", "(ザ ロスト)", "(El Olvidado)", "(El alma)", "(El perdido)", "(Judas oscuro)", "(Der Vergessene)", "(Die Seele)", "(Schwarzer Judas)", "(Der Verlorene)", "(더 포가튼)", "(더 소울)", "(블랙 유다)", "(더 로스트)")
        self.triple_words_chars = ("(Judas des Ombres)")

    def parse(self):
        """
        Parse the log file and return a TrackerState object,
        or None if the log file couldn't be found
        """

        self.opt = Options()
        # Attempt to load log_file
        if not self.__load_log_file():
            return None
        self.splitfile = self.content.splitlines()

        # This will become true if we are getting starting items
        self.getting_start_items = False

        # Process log's new output
        for current_line_number, line in enumerate(self.splitfile[self.seek:]):
            self.__parse_line(current_line_number, line)


        self.seek = len(self.splitfile)
        return self.state

    def __parse_line(self, line_number, line):
        """
        Parse a line using the (line_number, line) tuple
        """
        # In Afterbirth+, nearly all lines start with this.
        # We want to slice it off.
        info_prefix = '[INFO] - '
        if line.startswith(info_prefix):
            line = line[len(info_prefix):]

        # Messages printed by mods have this prefix.
        # strip it, so mods can spoof actual game log messages to us if they want to
        luadebug_prefix ='Lua Debug: '
        if line.startswith(luadebug_prefix):
            line = line[len(luadebug_prefix):]

        regexp_str_r = r"[|] Racing[+] (\d+).(\d+).(\d+) initialized."
        regexp_str_b = r"[|] The Babies Mod (\d+).(\d+).(\d+) initialized."
        regexp_str_i = r"[|] Achievement Randomizer (\d+).(\d+).(\d+) initialized."
        search_result_r = re.search(regexp_str_r, line)
        search_result_b = re.search(regexp_str_b, line)
        search_result_i = re.search(regexp_str_i, line)

        # Repentance and Repentance+ as well as AB and AB+ version messages both start with this text (Rep+ and AB+ have a + at the end)
        if line.startswith('Binding of Isaac: Repentance') or line.startswith('Binding of Isaac: Afterbirth') or line.startswith('Binding of Isaac: Rebirth'):
            self.__parse_version_number(line)
        if search_result_r is not None:
            self.state.racing_plus_version = "/ R+: "+ str(int(search_result_r.group(1))) + "." + str(int(search_result_r.group(2))) + "." + str(int(search_result_r.group(3))) + " "
        if search_result_b is not None:
            self.state.babies_mod_version = "/ Babies Mod: "+ str(int(search_result_b.group(1))) + "." + str(int(search_result_b.group(2))) + "." + str(int(search_result_b.group(3))) + " "
        if search_result_i is not None:
            self.state.IAR_version = "/ Achievement Randomizer: "+ str(int(search_result_i.group(1))) + "." + str(int(search_result_i.group(2))) + "." + str(int(search_result_i.group(3))) + " "
        if line.startswith('Loading PersistentData'):
            self.__parse_save(line)
        if line.startswith('Menu_OnlineLobby::notify_game_start()') or line.startswith('Saving screenshot...'):
            self.is_online_run = True
        if line.startswith('RNG Start Seed:'):
            self.__parse_seed(line, line_number)
        if line.startswith('Initialized player with Variant') and self.state.player == -1:
            self.__parse_player(line)
        if self.opt.game_version in ["Repentance", "Repentance+"] and line.startswith('Level::Init') and self.state.greedmode is None: # Store the line of the first floor in Repentance because we can detect if we are in greed mode only after this line in the log
            self.first_line = line
            self.curse_first_floor = ""
        elif line.startswith('Level::Init'):
            self.__parse_floor(line, line_number)   
        if line.startswith('Room'):
            self.__parse_room(line)
            if self.opt.game_version in ["Repentance", "Repentance+"]:
                self.detect_greed_mode(line, line_number)
                self.state.remove_additional_char_items()
        if line.startswith("Curse"):
            self.__parse_curse(line)
        if line.startswith("Spawn co-player!"):
            self.spawned_coop_baby = line_number + self.seek
        if re.search(r"Added \d+ Collectibles", line):
            self.log.debug("Reroll detected!")
            self.state.reroll()
        if line.startswith('Adding collectible '):
            self.__parse_item_add(line_number, line)
        if line.startswith('Gulping trinket ') or line.startswith('Adding smelted trinket '):
            self.__parse_trinket_gulp(line)
        if line.startswith('Removing collectible ') or line.startswith('Removing smelted trinket '):
            self.__parse_item_remove(line)
        if line.startswith('Executing command: reseed'):
            # racing+ re-generates floors if they contain duplicate rooms. we need to track that this is happening
            # so we don't erroneously think the entire run is being restarted when it happens on b1.
            self.reseeding_floor = True
        if line.startswith('Caught exception,'):
            self.__backup_log(crash=True)
        if line.startswith('Isaac has shut down'):
            self.__backup_log()
        if line.startswith('REBIRTH_ITEM_TRACKER_WRITE_TO_FILE'):
            self.__parse_mod_text(line)
        if line.startswith('REBIRTH_ITEM_TRACKER_REMOVE_COLLECTIBLE'):
            self.__parse_item_remove(line, forceRemoveActive=True)


    def __trigger_new_run(self, line_number):
        self.log.debug("Starting new run, seed: %s", self.current_seed)
        self.run_start_line = line_number + self.seek
        self.state.reset(self.current_seed, Options().game_version, self.state.racing_plus_version, self.state.babies_mod_version, self.state.IAR_version)

    def __parse_version_number(self, line):
        words = line.split()
        self.state.version_number = words[-1]

    def __parse_save(self,line):
        regexp_str = r"Loading PersistentData (\d+)"
        search_result = re.search(regexp_str, line)
        self.state.save = int(search_result.group(1)) if search_result is not None else 0

    def __parse_seed(self, line, line_number):
        """ Parse a seed line """
        # This assumes a fixed width, but from what I see it seems safe
        self.current_seed = line[16:25]
        space_split = line.split(" ")
        # Antibirth doesn't have a proper way to detect run resets
        # it will wipe the tracker when doing a "continue"
        if (self.opt.game_version in ["Repentance", "Repentance+"] and (space_split[6] in ('[New,', '[Daily,') or (space_split[6] == '[Continue,' and self.is_online_run == True))) or self.opt.game_version == "Antibirth":
            self.__trigger_new_run(line_number)
            self.is_online_run = False
        #Online runs in Repentance+ are a huge mess in the log, don't want to deal with that
        elif self.opt.game_version == "Repentance+" and space_split[6] == '[Net,':
            self.is_online_run = True
        elif (self.opt.game_version in ["Repentance", "Repentance+"] and space_split[6] == '[Continue,'):
            self.state.load_from_export_state()

    def __parse_player(self, line):
        regexp_str = r"Initialized player with Variant (\d+) and Subtype (\d+)"
        search_result = re.search(regexp_str, line)
        self.state.player = int(search_result.group(2)) if search_result is not None else 8 # Put it on Lazarus by default

    def __parse_room(self, line):
        """ Parse a room line """
        if 'Start Room' not in line:
            self.getting_start_items = False

        match = re.search(r"Room (.+?)\(", line)
        if match:
            room_id = match.group(1)
            self.state.change_room(room_id)

    def detect_greed_mode(self, line, line_number):
        # Detect if we're in Greed mode or not in Repentance. We must do a ton of hacky things to show the first floor with curses because we can't detect greed mode in one line anymore
        match = re.search(r"Room (.+?)\(", line)
        if match:
            room_id = match.group(1)
            if room_id == '18.1000': # Genesis room
                self.state.item_list = []
                self.state.set_transformations()
            elif self.state.greedmode is None:
                self.state.greedmode = room_id in self.greed_mode_starting_rooms
                self.__parse_floor(self.first_line, line_number)
                self.__parse_curse(self.curse_first_floor)

    def __parse_floor(self, line, line_number):
        """ Parse the floor in line and push it to the state """
        # Create a floor tuple with the floor id and the alternate id
        if self.opt.game_version == "Afterbirth" or self.opt.game_version == "Afterbirth+" or self.opt.game_version in ["Repentance", "Repentance+"]:
            regexp_str = r"Level::Init m_Stage (\d+), m_StageType (\d+)"
        elif self.opt.game_version == "Rebirth" or self.opt.game_version == "Antibirth":
            regexp_str = r"Level::Init m_Stage (\d+), m_AltStage (\d+)"
        else:
            return
        search_result = re.search(regexp_str, line)
        if search_result is None:
            self.log.debug("log.txt line doesn't match expected regex\nline: \"" + line+ "\"\nregex:\"" + regexp_str + "\"")
            return

        floor = int(search_result.group(1))
        alt = search_result.group(2)
        self.getting_start_items = True

        # we use generation of the first floor as our trigger that a new run started.
        # in racing+, it doesn't count if the game is currently in the process of "reseeding" that floor.
        # in antibirth, this doesn't work at all; instead we have to use the seed being printed as our trigger.
        # that means if you s+q in antibirth, it resets the tracker.
        # In Repentance, Downpour 1 and Dross 1 are considered Stage 1.
        # So we need to add a condition to avoid tracker resetting when entering those floors.
        # In Repentance, don't trigger a new run on floor 1 because of the R Key item
        if self.reseeding_floor:
            self.reseeding_floor = False
        elif floor == 1 and self.opt.game_version != "Antibirth" and self.opt.game_version not in ["Repentance", "Repentance+"]:
            self.__trigger_new_run(line_number)

        # Special handling for the Cathedral and The Chest and Afterbirth
        if self.opt.game_version == "Afterbirth" or self.opt.game_version == "Afterbirth+" or self.opt.game_version in ["Repentance", "Repentance+"]:
            self.log.debug("floor")
            # In Afterbirth, Cath is an alternate of Sheol (which is 10)
            # and Chest is an alternate of Dark Room (which is 11)
            # In Repentance, alt paths are same stage as their counterparts (ex: Basement 1 = Downpour 1)
            if alt == '4' or alt == '5':
                floor += 15
            elif floor == 10 and alt == '0':
                floor -= 1
            elif floor == 11 and alt == '1':
                floor += 1
            elif floor == 9:
                floor = 13
            elif floor == 12:
                floor = 14
            elif floor == 13:
                floor = 15    
        else:
            # In Rebirth, floors have different numbers
            if alt == '1' and (floor == 9 or floor == 11):
                floor += 1
        floor_id = 'f' + str(floor)

        # Greed mode
        if (alt == '3' and self.opt.game_version not in ["Repentance", "Repentance+"]) or (self.opt.game_version in ["Repentance", "Repentance+"] and self.state.greedmode):
            floor_id += 'g'

        self.state.add_floor(Floor(floor_id))
        self.state.export_state()
        return True

    def __parse_curse(self, line):
        """ Parse the curse and add it to the last floor """
        if self.state.racing_plus_version != "":
            return
        if self.curse_first_floor == "":
            self.curse_first_floor = line
        elif self.state.greedmode is not None:
            self.curse_first_floor = ""
        if line.startswith("Curse of the Labyrinth!") or (self.curse_first_floor == "Curse of the Labyrinth!" and self.opt.game_version in ["Repentance", "Repentance+"]):
            self.state.add_curse(Curse.Labyrinth)
        if line.startswith("Curse of Blind") or (self.curse_first_floor == "Curse of Blind" and self.opt.game_version in ["Repentance", "Repentance+"]):
            self.state.add_curse(Curse.Blind)

    def __parse_item_add(self, line_number, line):
        # In Repentance+ they added 'from pool x' at the end of an item taken so we remove it to be able to show the multi char icons
        regexp_str = r" from pool .*"
        search_result = re.search(regexp_str, line)
        line = line.replace(search_result.group(), "")

        """ Parse an item and push it to the state """
        if len(self.splitfile) > 1 and self.splitfile[line_number + self.seek - 1] == line:
            self.log.debug("Skipped duplicate item line from baby presence")
            return False
        is_Jacob_item = line.endswith(self.jacob_names) and self.opt.game_version in ["Repentance", "Repentance+"] and self.state.player == 19
        is_Esau_item = line.endswith(self.esau1_names) and self.opt.game_version in ["Repentance", "Repentance+"] and self.state.player == 19
        if self.state.player in (14, 33): # Don't show keeper head on keeper and tainted keeper 
            is_Strawman_item = "player 0" not in line and line.endswith(self.keeper_names) and self.state.contains_item('667')
            is_EsauSoul_item = "player 0" not in line and line.endswith(self.esau_names)
        elif self.state.player == 19:
            is_Strawman_item = line.endswith(self.keeper_names) and self.state.contains_item('667')
            is_EsauSoul_item = "player 0" not in line and "player 1 " not in line and line.endswith(self.esau_names)
        else:
            is_Strawman_item = line.endswith(self.keeper_names) and self.state.contains_item('667')
            is_EsauSoul_item = "player 0" not in line and line.endswith(self.esau_names)

        if self.state.player == 19 and not is_Esau_item and not is_Jacob_item and not is_Strawman_item and not is_EsauSoul_item: # This is when J&E transform into another character
            self.state.player = 8 # Put it on Lazarus by default just in case we got another Anemic
        elif self.state.player not in (19, 37) and is_Jacob_item:
            self.state.player = 19

        space_split = line.split(" ")
        numeric_id = space_split[2] # When you pick up an item, this has the form: "Adding collectible 105 (The D6)" or "Adding collectible 105 (The D6) to Player 0 (Isaac)" in Repentance
        double_word_char = line.endswith(self.double_words_chars)
        triple_word_char = line.endswith(self.triple_words_chars)
        if self.opt.game_version in ["Repentance", "Repentance+"] and triple_word_char:
            item_name = " ".join(space_split[3:-4])[1:-11]
        elif self.opt.game_version in ["Repentance", "Repentance+"] and double_word_char:
            item_name = " ".join(space_split[3:-4])[1:-4]
        elif self.opt.game_version in ["Repentance", "Repentance+"]:
            item_name = " ".join(space_split[3:-4])[1:-1]
        else:
            item_name = " ".join(space_split[3:])[1:-1]

        item_id = ""

        if int(numeric_id) < 0:
                numeric_id = "0" if item_name == "G FUEL!" else "-1"

        # Check if we recognize the numeric id
        if Item.contains_info(numeric_id):
            item_id = numeric_id
        else:
            # it might be a modded custom item. let's see if we recognize the name
            item_id = Item.modded_item_id_prefix + item_name
            if not Item.contains_info(item_id):
                item_id = "NEW"

        self.log.debug("Picked up item. id: %s, name: %s", item_id, item_name)
        if ((line_number + self.seek) - self.spawned_coop_baby) < (len(self.state.item_list) + 10) \
                and self.state.contains_item(item_id):
            self.log.debug("Skipped duplicate item line from baby entry")
            return False

        # It's a blind pickup if we're on a blind floor and we don't have the Black Candle
        blind_pickup = self.state.last_floor.floor_has_curse(Curse.Blind) and not self.state.contains_item('260')
        if not (numeric_id == "214" and ((self.state.contains_item('214') and self.state.contains_item('332')) or (self.state.player == 8 and self.state.contains_item('214')))):
            added = self.state.add_item(Item(item_id, numeric_id, self.state.last_floor, self.getting_start_items, blind=blind_pickup, is_Jacob_item=is_Jacob_item, is_Esau_item=is_Esau_item, is_Strawman_item=is_Strawman_item, is_EsauSoul_item=is_EsauSoul_item, shown=Item.get_item_info(item_id).shown))
            if not added:
                self.log.debug("Skipped adding item %s to avoid space-bar duplicate", item_id)
        else:
            self.log.debug("Skipped adding Anemic from Lazarus Rags because we already have Anemic")

        if item_id in ("144", "238", "239", "278", "388", "550", "552", "626", "627"):
            self.__parse_add_multi_items()
        self.state.export_state()
        return True

    def __parse_add_multi_items(self):
        """Add custom sprites for multi-segmented items like Super Bum, key pieces or knife pieces"""
        # item.info.shown = False is for not showing the item on the tracker
        # item.shown = False is for the export_state function to store the actual shown value instead of the initial value item.info.shown
        if self.state.contains_item('238') and self.state.contains_item('239') and not self.state.contains_item('3000'):
            for item in reversed(self.state.item_list):
                if item.item_id in ("238", "239"):
                    item.info.shown = False
                    item.shown = False
            self.state.add_item(Item("3000", "3000", floor=self.state.last_floor))
        elif self.state.contains_item('550') and self.state.contains_item('552'):
            for item in reversed(self.state.item_list):
                if item.item_id == "550":
                    item.info.shown = False
                    item.shown = False
        elif self.state.contains_item('144') and self.state.contains_item('278') and self.state.contains_item('388') and not self.state.contains_item('3001') and self.opt.game_version != "Rebirth" and self.opt.game_version != "Antibirth":
            for item in reversed(self.state.item_list):
                if item.item_id in ("144", "278", "388"):
                    item.info.shown = False
                    item.shown = False
            self.state.add_item(Item("3001", "3001", floor=self.state.last_floor))
        elif self.state.contains_item('626') and self.state.contains_item('627') and not self.state.contains_item('3002'):
            for item in reversed(self.state.item_list):
                if item.item_id in ("626", "627"):
                    item.info.shown = False
                    item.shown = False
            self.state.add_item(Item("3002", "3002", floor=self.state.last_floor))    

    def __parse_trinket_gulp(self, line):
        """ Parse a (modded) trinket gulp and push it to the state """
        space_split = line.split(" ")
        # When using a mod like racing+ on AB+, a trinket gulp has the form: "Gulping trinket 10"
        # In Repentance, a gulped trinket has the form : "Adding smelted trinket 10"
        if self.opt.game_version in ["Repentance", "Repentance+"] and int(space_split[3]) > 30000:
            numeric_id = str(int(space_split[3]))
        elif self.opt.game_version in ["Repentance", "Repentance+"]:
            numeric_id = str(int(space_split[3]) + 2000) # the tracker hackily maps trinkets to items 2000 and up.
        else:
            numeric_id = str(int(space_split[2]) + 2000) # the tracker hackily maps trinkets to items 2000 and up.
        is_Jacob_item = line.endswith(self.jacob_names) and self.opt.game_version in ["Repentance", "Repentance+"] and self.state.player == 19
        is_Esau_item = line.endswith(self.esau1_names) and self.opt.game_version in ["Repentance", "Repentance+"] and self.state.player == 19

        # Check if we recognize the numeric id
        if Item.contains_info(numeric_id):
            item_id = numeric_id
        else:
            item_id = "NEW"
        
        numeric_id = "t" + str(numeric_id) if item_id == "NEW" else item_id

        self.log.debug("Gulped trinket: %s", item_id)

        added = self.state.add_item(Item(item_id, numeric_id, self.state.last_floor, self.getting_start_items, is_Jacob_item=is_Jacob_item, is_Esau_item=is_Esau_item))
        if not added:
            self.log.debug("Skipped adding item %s to avoid space-bar duplicate", item_id)
        self.state.export_state()
        return True

    def __parse_item_remove(self, line, forceRemoveActive=False):
        """ Parse an item and remove it from the state """
        if forceRemoveActive:
            line = line.replace("REBIRTH_ITEM_TRACKER_REMOVE_COLLECTIBLE ","")
        space_split = line.split(" ") # Hacky string manipulation
        double_word_char = line.endswith("(The Lost)") or line.endswith("(The Forgotten)") or line.endswith("(The Soul)") or line.endswith("(Black Judas)") or line.endswith("(Random Baby)")
        # When you lose an item, this has the form: "Removing collectible 105 (The D6)"
        if self.opt.game_version in ["Repentance", "Repentance+"] and space_split[2] == "trinket" and int(space_split[3]) < 30000:
            item_id = str(int(space_split[3]) + 2000)
            item_name = " ".join(space_split[3:-5])[3:-1] if double_word_char else " ".join(space_split[3:-4])[3:-1]
        else:
            item_id = space_split[2]
            item_name = " ".join(space_split[3:-5])[1:-1] if double_word_char else " ".join(space_split[3:-4])[1:-1]
        # Check if the item ID exists
        if Item.contains_info(item_id):
            removal_id = item_id
        else:
            # that means it's probably a custom item
            removal_id = Item.modded_item_id_prefix + item_name

        self.log.debug("Removed item. id: %s", removal_id)

        if item_id in ("144", "238", "239", "278", "388", "626", "627"):
            self.__parse_remove_multi_items(item_id=item_id)

        if item_id == "667":
            self.state.remove_additional_char_items(strawman=True)

        # A check will be made inside the remove_item function
        # to see if this item is actually in our inventory or not.
        return self.state.remove_item(removal_id, forceRemoveActive)

    def __parse_remove_multi_items(self, item_id):
        """Remove custom sprites for multi-segmented items like Super Bum, key pieces or knife pieces"""
        if item_id in ("238", "239"):
            for item in reversed(self.state.item_list):
                if item.item_id in ("238", "239"):
                    item.info.shown = True
            self.state.remove_item("3000")
        elif item_id in ("144", "278", "388"):
            for item in reversed(self.state.item_list):
                if item.item_id in ("144", "278", "388"):
                    item.info.shown = True
            self.state.remove_item("3001")
        elif item_id in ("626", "627"):
            for item in reversed(self.state.item_list):
                if item.item_id in ("626", "627"):
                    item.info.shown = True
            self.state.remove_item("3002")       

    def __parse_mod_text(self, line):
        line = line.replace("REBIRTH_ITEM_TRACKER_WRITE_TO_FILE ","")
        f = open("../mod_text.txt", "w")
        f.write(line)
        f.close()

    def __load_log_file(self):
        if self.log_file_path is None:
            return False

        if self.log_file_handle is None:
            self.log_file_handle = open(self.log_file_path, 'r', encoding='utf-8', errors='replace')

        cached_length = len(self.content)
        file_size = os.path.getsize(self.log_file_path)

        if cached_length > file_size or cached_length == 0: # New log file or first time loading the log
            self.reset()
            self.content = open(self.log_file_path, 'r', encoding='utf-8', errors='replace').read()
        elif cached_length < file_size:  # Append existing content
            self.log_file_handle.seek(cached_length + 1)
            self.content += self.log_file_handle.read()
        return True


    def __backup_log(self, crash=False):
        if self.log_file_path is None:
            return False

        logsTarget = '/backup logs'
        if not os.path.exists(self.wdir_prefix + logsTarget):
            os.mkdir(self.wdir_prefix + logsTarget)

        target = self.wdir_prefix + logsTarget
        racingPlusLogsTarget = '/Racing+ logs'

        if self.state.racing_plus_version != "":
            if not os.path.exists(target + racingPlusLogsTarget):
                os.mkdir(target + racingPlusLogsTarget)
            target += racingPlusLogsTarget

        now = datetime.now()
        logTime = now.strftime("%d-%m-%Y %H-%M-%S")

        target += '/' + logTime
        if crash:
            target = target + " [crash]"

        if self.state.racing_plus_version != "":
            racingPlusVersion = self.state.racing_plus_version.replace("/ R+: ", "")
            target = target + " - " + racingPlusVersion

        versionNumber = self.state.version_number.replace("v1", "1").replace(".0000", "")
        target = target + " - " + versionNumber + ".txt"

        shutil.copy(self.log_file_path, target)

        if os.path.exists(self.wdir_prefix + logsTarget + racingPlusLogsTarget):
            self.__delete_last_logs("backup logs/", 1)
            self.__delete_last_logs("backup logs/Racing+ logs/", 0)
        else:
            self.__delete_last_logs("backup logs/", 0)



    def __delete_last_logs(self, folder, numFolders):
        path = self.wdir_prefix + folder
        mtime = lambda f: os.stat(os.path.join(path, f)).st_mtime
        sorted_ls = list(sorted(os.listdir(path), key=mtime))
        if len(sorted_ls) >= 200:
            del_list = sorted_ls[numFolders:(len(sorted_ls)-200)]
            for file in del_list:
                os.remove(path + file)

