"""This module handles anything related to the item tracker's state"""
import json
from game_objects.item  import Item, ItemInfo
from game_objects.floor import Floor
from game_objects.serializable import Serializable
from options import Options

class TrackerState(Serializable):
    """This class represents a tracker state, and handle the logic to
    modify it while keeping it coherent
    """
    serialize = [('seed', str),
                 ('floor_list', list),
                 ('item_list', list),
                 ('tracker_version', str),
                 ('game_version', str),
                 ('racing_plus_version', str),
                 ('babies_mod_version', str),
                 ('IAR_version', str),
                 ('version_number', str),
                 ('player', int),
                 ('player_transforms', dict),
                 ('player2_transforms', dict),
                 ('greedmode', bool)]
    def __init__(self, seed, tracker_version, game_version, racing_plus_version, babies_mod_version, IAR_version, version_number, player):
        self.reset(seed, game_version, racing_plus_version, babies_mod_version, IAR_version)
        self.tracker_version = tracker_version
        self.version_number = version_number
        self.racing_plus_version = racing_plus_version
        self.babies_mod_version = babies_mod_version
        self.IAR_version = IAR_version
        self.save = 0
        self.player = player

    def reset(self, seed, game_version, racing_plus_version, babies_mod_version, IAR_version):
        """
        Reset a run to a given string
        This should be enough to enable the GC to clean everything from the previous run
        """
        # When the tracker state has been restarted, put this to True
        # The view can then put it to false once it's been rendered
        self.modified = True
        self.seed = seed
        self.game_version = game_version
        self.racing_plus_version = racing_plus_version
        self.babies_mod_version = babies_mod_version
        self.IAR_version = IAR_version
        self.greedmode = False
        self.floor_list = []
        self.room_id = "none"
        self.item_list = []
        self.player = -1
        self.player_stats = {}
        self.player_transforms = {}
        self.player2_transforms = {} # For Esau
        for stat in ItemInfo.stat_list:
            self.player_stats[stat] = 0.0

        if Options().game_version in ["Repentance", "Repentance+"]:  # Repentance allows multiple occurrence of the same item to count in transformations so transformation counts must be arrays instead of objects
            self.set_transformations()
        else:
            for transform in ItemInfo.transform_list:
                self.player_transforms[transform] = set()

    def set_transformations(self):
        """ Reset transformation dicts, also used when Genesis is used """
        for transform in ItemInfo.transform_list:
            self.player_transforms[transform] = []
            self.player2_transforms[transform] = []

    def add_floor(self, floor):
        """ Add a floor to the current run """
        self.floor_list.append(floor)
        self.modified = True

    @property
    def last_floor(self):
        """
        Get current floor
        If no floor is in the floor list, create a default one
        """
        if len(self.floor_list) == 0:
            self.add_floor(Floor("f1"))
        return self.floor_list[-1]

    def add_item(self, item):
        """
        Add an item to the current run, and update player's stats accordingly
        Return a boolean.
        The boolean is true if the item has been added, false otherwise.
        """
        # Ignore repeated pickups of space bar items
        if not (item.info.space and item in self.item_list) and item.shown:
            self.item_list.append(item)
            if not item.is_Strawman_item:
                self.__add_stats_for_item(item)
            self.modified = True
            return True
        else:
            return False

    def remove_item(self, item_id, forceRemoveActive=False):
        """
        Remove the given item from the current run, and update player's stats accordingly.
        If we have multiples of that item, the removed item is the most recent of them.
        Return a boolean.
        The boolean is true if an item has been removed, false otherwise.
        """

        # Find the item by iterating backwards through the list
        foundItem = False
        for item in reversed(self.item_list):
            if item.item_id == item_id and (forceRemoveActive or not item.info.space):
                foundItem = True
                break

        # We don't have this item in our inventory
        if not foundItem:
            return False

        self.item_list.remove(item)
        self.__remove_stats_for_item(item)
        self.modified = True
        self.export_state()
        return True

    def remove_additional_char_items(self, strawman=False):
        """
        Remove every item from the extra Esau spawned by the Soul of Jacob&Esau or from Strawman
        """
        items_removed = 0
        if strawman:
            for item in reversed(self.item_list):
                if item.is_Strawman_item:
                    item.info.shown = False
                    item.shown = False
                    items_removed += 1
        else:
            for item in reversed(self.item_list):
                if item.is_EsauSoul_item and item.shown:
                    item.info.shown = False
                    item.shown = False
                    items_removed += 1

        if items_removed != 0: # Only change tracker state if we removed at least one item because this function is called at every room change
            self.modified = True

        return True

    def multi_items(self):
        """Remove multi-segmented items when quest items are completed and you watch someone else"""
        # item.info.shown = False is for not showing the item on the tracker
        # item.shown = False is for the export_state function to store the actual shown value instead of the initial value item.info.shown
        if self.contains_item('238') and self.contains_item('239') and not self.contains_item('3000'):
            for item in reversed(self.item_list):
                if item.item_id in ("238", "239"):
                    item.info.shown = False
                    item.shown = False
        elif self.contains_item('550') and self.contains_item('552'):
            for item in reversed(self.item_list):
                if item.item_id == "550":
                    item.info.shown = False
                    item.shown = False
        elif self.contains_item('144') and self.contains_item('278') and self.contains_item('388') and not self.contains_item('3001'):
            for item in reversed(self.item_list):
                if item.item_id in ("144", "278", "388"):
                    item.info.shown = False
                    item.shown = False
        elif self.contains_item('626') and self.contains_item('627') and not self.contains_item('3002'):
            for item in reversed(self.item_list):
                if item.item_id in ("626", "627"):
                    item.info.shown = False
                    item.shown = False

    @property
    def last_item(self):
        """
        Get last item picked up
        Can return None !
        """
        if len(self.item_list) > 0:
            return self.item_list[-1]
        else:
            return None

    def contains_item(self, item_id):
        """ Looks for the given item_id in our item_list """
        return len([x for x in self.item_list if x.item_id == item_id]) >= 1

    def reroll(self):
        """ Tag every (non-spacebar) items as rerolled """
        for item in self.item_list:
            # D6 can't be rolled in rep r+ since it's a pocket item
            if not (self.racing_plus_version != "" and item.item_id == "105"):
                item.rerolled(self.player)
        [self.__remove_stats_for_item(item) for item in self.item_list]

    # Add curse to last floor
    def add_curse(self, curse):
        """ Add a curse to current floor """
        self.last_floor.add_curse(curse)

    def change_room(self, room_id):
        self.room_id = room_id

    def drawn(self):
        """ Tag this state as rendered """
        self.modified = False

    @staticmethod
    def from_valid_json(json_dic, *args):
        """ Create a state from a type-checked dic """
        state = TrackerState(json_dic['seed'], json_dic['tracker_version'], json_dic['game_version'], json_dic['racing_plus_version'], json_dic['babies_mod_version'], json_dic['IAR_version'], json_dic['version_number'], json_dic['player'])
        # The order is important, we want a list of legal floors the item can
        # be picked up on before parsing items
        for floor_dic in json_dic['floor_list']:
            floor = Floor.from_json(floor_dic)
            if not floor:
                return None
            state.add_floor(floor)
        for item_dic in json_dic['item_list']:
            item = Item.from_json(item_dic, state.floor_list)
            if not item:
                return None
            state.add_item(item)
            state.multi_items()

        return state

    def __add_stats_for_item(self, item):
        """
        Update player's stats with the given item.
        """
        item_info = item.info
        for stat in ItemInfo.stat_list:
            if not item_info[stat]:
                continue
            change = float(item_info[stat])
            self.player_stats[stat] += change
        for transform in ItemInfo.transform_list:
            if not item_info[transform]:
                continue
            if Options().game_version in ["Repentance", "Repentance+"]: # Repentance allows multiple occurrence of the same item to count in transformations
                if item.is_Esau_item:
                    self.player2_transforms[transform].append(item)
                    if item.item_id == "32937": # Golden Kid's Drawing
                        self.player2_transforms[transform].append(1)
                elif not item.is_Strawman_item and not item.is_EsauSoul_item:
                    self.player_transforms[transform].append(item)
                    if item.item_id == "32937": # Golden Kid's Drawing
                        self.player_transforms[transform].append(1)
            else:
                self.player_transforms[transform].add(item)

    def __remove_stats_for_item(self, item):
        """
        Update player's stats with the given item.
        """
        item_info = item.info
        for stat in ItemInfo.stat_list:
            if not item_info[stat]:
                continue
            change = float(item_info[stat])
            self.player_stats[stat] -= change

        for transform in ItemInfo.transform_list:
            if not item_info[transform]:
                continue
            if not item.info.space and Options().game_version in ["Repentance", "Repentance+"] and item.is_Esau_item and item in self.player2_transforms[transform]:
                self.player2_transforms[transform].remove(item)
            elif not item.info.space and Options().game_version in ["Repentance", "Repentance+"] and self.player != 21 and item in self.player_transforms[transform] and not item.is_Esau_item:
                self.player_transforms[transform].remove(item)

    def export_state(self):
        # Debug function to write the state to a json file
        data = self.get_export_state()
        if data == {}:
            with open("../export_state.json", "w") as state_file:
                if self.game_version in ["Repentance", "Repentance+"] or self.game_version == "Afterbirth+":
                    state_file.write(json.dumps({self.game_version:{self.save : self}}, cls=TrackerStateEncoder, sort_keys=True))
                else:
                    state_file.write(json.dumps({self.game_version:self}, cls=TrackerStateEncoder, sort_keys=True))
        else:
            if self.game_version in ["Repentance", "Repentance+"] or self.game_version == "Afterbirth+":
                if self.game_version in data:
                    data[self.game_version][str(self.save)] = self
                else:
                    data[self.game_version] = {self.save : self}
            else:
                data[self.game_version] = self
            with open("../export_state.json", "w") as state_file:
                state_file.write(json.dumps(data, cls=TrackerStateEncoder, sort_keys=True))

    def load_from_export_state(self):
            new_floor_list = []
            new_item_list = []
            data = self.get_export_state()
            try:
                if self.game_version in ["Repentance", "Repentance+"] or self.game_version == "Afterbirth+":
                    data = data[self.game_version][str(self.save)]
                else:
                    data = data[self.game_version]
                self.seed = data['seed']
                self.player = data['player']
                self.greedmode = data['greedmode']
                for floor in data['floor_list']:
                    new_floor = Floor(floor["floor_id"], floor["curse"])
                    new_floor_list.append(new_floor)
                self.floor_list = new_floor_list
                for item in data['item_list']:
                    new_item = Item(flagstr=item["flags"], item_id=item['item_id'], numeric_id=item['numeric_id'], floor=Floor(floor_id=item['floor_id']))
                    new_item.info.shown = item["shown"]
                    new_item_list.append(new_item)
                self.item_list = new_item_list
                self.player_transforms = data['player_transforms']
                if self.player == 19:
                    self.player2_transforms = data['player2_transforms']
                self.modified = True
            except:
                return True    

    def get_export_state(self):
        try:
            with open("../export_state.json", "r") as state_file:
                data = json.loads(state_file.read())
        except:
            data = {}
        return data

            

class TrackerStateEncoder(json.JSONEncoder):
    """ An encoder to provide to the json.load method, which handle game objects """
    def default(self, obj):
        try:
            if isinstance(obj, Serializable):
                return obj.to_json()
            return obj.__dict__
        except:
            return list(obj)    
