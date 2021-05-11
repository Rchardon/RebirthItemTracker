"""This module handles anything related to the item tracker's state"""
import logging
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
                 ('player', str),
                 ('player_transforms', list),
                 ('player2_transforms', list),
                 ('greedmode', bool)]
    def __init__(self, seed, tracker_version, game_version):
        self.reset(seed, game_version)
        self.tracker_version = tracker_version
        self.version_number = ''
        self.save = 0

    def reset(self, seed, game_version):
        """
        Reset a run to a given string
        This should be enough to enable the GC to clean everything from the previous run
        """
        # When the tracker state has been restarted, put this to True
        # The view can then put it to false once it's been rendered
        self.modified = True
        self.seed = seed
        self.game_version = game_version
        self.greedmode = None
        self.floor_list = []
        self.room_id = "none"
        self.item_list = []
        self.player = None
        self.player_stats = {}
        self.player_transforms = {}
        self.player2_transforms = {} # For Esau
        self.savequit = False
        for stat in ItemInfo.stat_list:
            self.player_stats[stat] = 0.0

        if Options().game_version == "Repentance":  # Repentance allows multiple occurence of the same item to count in transformations so transformation counts must be arrays instead of objects
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
        if not (item.info.space and item in self.item_list) and item.info['shown']:
            self.item_list.append(item)
            self.__add_stats_for_item(item)
            self.modified = True
            return True
        else:
            return False    

    def remove_item(self, item_id):
        """
        Remove the given item from the current run, and update player's stats accordingly.
        If we have multiples of that item, the removed item is the most recent of them.
        Return a boolean.
        The boolean is true if an item has been removed, false otherwise.
        """

        # Find the item by iterating backwards through the list
        foundItem = False
        for item in reversed(self.item_list):
            if item.item_id == item_id and not item.info.space:
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

    def remove_item_from_soul(self):
        """
        Remove every item from the extra Esau spawned by the Soul of Jacob&Esau
        """

        for item in reversed(self.item_list):
            if item.is_Esau_item and item.info.shown:
                item.info.shown = False
                self.modified = True

        return True

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
        [item.rerolled() for item in self.item_list]
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
        state = TrackerState(json_dic['seed'], json_dic['tracker_version'], json_dic['game_version'])
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
            if Options().game_version == "Repentance": # Repentance allows multiple occurence of the same item to count in transformations
                if item.is_Esau_item:
                    self.player2_transforms[transform].append(item)
                    if item.item_id == "32937": # Golden Kid's Drawing
                        self.player2_transforms[transform].append(1)
                else:
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
            if not item.info.space and Options().game_version == "Repentance" and item.is_Esau_item and item in self.player2_transforms[transform]:
                self.player2_transforms[transform].remove(item)
            elif not item.info.space and Options().game_version == "Repentance" and self.player != 21 and item in self.player_transforms[transform] and not item.is_Esau_item:
                self.player_transforms[transform].remove(item)

    def export_state(self):
        # Debug function to write the state to a json file
        data = self.get_export_state()
        if data == {}:
            with open("../export_state.json", "w") as state_file:
                if self.game_version == "Repentance" or self.game_version == "Afterbirth+":
                    state_file.write(json.dumps({self.game_version:{self.save : self}}, cls=TrackerStateEncoder, sort_keys=True))
                else:
                    state_file.write(json.dumps({self.game_version:self}, cls=TrackerStateEncoder, sort_keys=True))
        else:
            if self.game_version == "Repentance" or self.game_version == "Afterbirth+":
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
                if self.game_version == "Repentance" or self.game_version == "Afterbirth+":
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
                    new_item = Item(flagstr=item["flags"], item_id=item['item_id'], floor=Floor(floor_id=item['floor_id']))
                    new_item_list.append(new_item)
                self.item_list = new_item_list
                self.player_transforms = data['player_transforms']
                if self.player == "19":
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
