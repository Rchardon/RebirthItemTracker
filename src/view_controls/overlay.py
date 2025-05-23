"""
This module deals with everything related to the overlay text generated,
as well as formatting how to display stats
"""
from game_objects.item  import ItemInfo

class Overlay(object):
    """The main class to handle output to overlay text files"""
    def __init__(self, prefix, tracker_state):
        self.state = tracker_state
        self.prefix = prefix

    @staticmethod
    def format_value(value):
        """Format a float value for displaying"""
        # NOTE this is not only used in this class
        # Round to 2 decimal places then ignore trailing zeros and trailing periods
        # Doing just 'rstrip("0.")' breaks on "0.00"
        display = format(value, ".2f").rstrip("0").rstrip(".")

        # For example, set "0.6" to ".6"
        if abs(value) < 1 and value != 0:
            display = display.lstrip("0")

        if value > -0.00001:
            display = "+" + display
        return display

    @staticmethod
    def format_transform(transform_set):
        """Format a transform_set for displaying"""
        # NOTE this is not only used in this class
        if len(transform_set) >= 3:
            return "yes"
        else:
            return str(len(transform_set))

    def update_stats(self, transform_list=None):
        """
        Update file content for a subset (or all) the player's stats.
        """
        if transform_list is None:
            transform_list = ItemInfo.transform_list
        for transform in transform_list:
            if self.state.player == 19:
                display = Overlay.format_transform(self.state.player_transforms[transform]) + " - " + Overlay.format_transform(self.state.player2_transforms[transform])
                with open(self.prefix + "overlay text/" + transform + ".txt", "w+") as sfile:
                    sfile.write(display + "/3")
            else:    
                display = Overlay.format_transform(self.state.player_transforms[transform])
                with open(self.prefix + "overlay text/" + transform + ".txt", "w+") as sfile:
                    sfile.write(display + "/3")

    def update_last_item_description(self):
        """Update the overlay file for item pickup description"""
        item = self.state.last_item
        if item:
            desc = item.info.name
            desc += ": " + item.generate_item_description()
        else:
            desc = ""
        with open(self.prefix + "overlay text/itemInfo.txt", "w+") as sfile:
            sfile.write(desc)

    def update_seed(self):
        """Update the overlay file for the seed"""
        with open(self.prefix + "overlay text/seed.txt", "w+") as sfile:
            sfile.write(self.state.seed)

    def update_game_version_number(self):
        """Update the overlay file for the game version number"""
        with open(self.prefix + "overlay text/game_version_number.txt", "w+") as sfile:
            sfile.write(self.state.version_number)
