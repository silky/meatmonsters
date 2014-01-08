import time
import os
import glob
import sys
import re
import random
import json
import base64 
import hashlib
from random import choice
from socketIO_client import SocketIO

class Monster(object):
    """
    A Monster is a bot instance, created from a directory containing an attributes.json
    file plus a collection of gifs and text files for each defined action.
    """

    @staticmethod
    def get_gif (filename):
        """get a gif from the filesystem and base64 encode it"""

        with open (filename, "rb") as image_file:
            data =  base64.b64encode(image_file.read())
            gif = "data:image/gif;base64," + data
            return gif

    @staticmethod
    def get_txt (filename):
        """create a collection from a text file"""

        with open (filename, "r") as text_file:
            lines = [line.rstrip() for line in text_file.readlines()]
        return lines

    def __init__(self, files):
        """initialize a bot from a directory"""

        with open (os.sep.join([files, "attributes.json"]), 'r') as conf:
            self.config = json.load(conf)
        
        self.name = self.config["name"]
        self.actions = {} 
        self.triggers = {}
        
        for action, triggers in self.config["actions"].items():
            if action not in self.actions:
                self.actions[action] = {"gifs":[], "txts":[]}

            gif_blob = os.sep.join([files, action]) + "*.gif"
            for gif_path in glob.glob(gif_blob):
                self.actions[action]["gifs"].append(Monster.get_gif(gif_path))

            txt_name = ".".join([action, "txt"])
            txt_path = os.sep.join([files, txt_name])
            self.actions[action]["txts"] = Monster.get_txt(txt_path)

            for trigger in triggers:
                compiled = re.compile(trigger, re.IGNORECASE)
                self.triggers[compiled] = {"monster":self.name, "action":action}

    def action(self, action):
        """return information for a called action"""

        values = {}
        values["message"] = choice(self.actions[action]["txts"])
        values["picture"] = choice(self.actions[action]["gifs"])
        values["fingerprint"] = self.name.zfill(32)
        return values

class MeatMonsters(object):
    """
    MeatMonsters is a framework for loading a collection of Monsters,
    connecting them to meatspace and dispatching commands to them
    """

    def __init__(self):
        """initialize a MeatMonsters collection from a config file"""

        with open ('meatmonsters.json', 'r') as conf:
            self.config = json.load(conf)

        self.api_key = self.config["key"]
        self.address = self.config["address"]
        self.monsters_dir = "./monsters/"

        self.debug = True
        self.monsters = {}
        self.triggers = {}
        self.count = 0
        self.load_monsters()
        self.last_bot = time.time()

    def load_monsters(self):
        """load all monsters from monster subdirectory"""

        for monster_subdir in os.walk(self.monsters_dir).next()[1]:
            monster_path = os.sep.join([self.monsters_dir, monster_subdir])
            monster = Monster(files=monster_path)
            self.monsters[monster.name] = monster
            for trigger, action in monster.triggers.items():
                self.triggers[trigger] = action

    def get_post (self, data):
        """extract wanted information from meatspace post"""

        post = {}
        post["key"] = data["chat"]["key"]
        post["message"] = data["chat"]["value"]["message"]
        return post

    def get_message (self, reply, image, fingerprint):
        """given a reply string and an image, construct a response"""

        message = {}
        message ['apiKey'] = self.api_key
        message ['message'] = reply
        message ['fingerprint'] = fingerprint
        message ['picture'] = image
        return message

    def send_message (self, reply, image, fingerprint):
        """send a message to meatspace"""

        SocketIO(self.address).emit('message', self.get_message(reply, image, fingerprint))

    def on_message(self, *args):
        """handles incoming messages from meatspace"""
        self.count = self.count + 1
        if self.count > 10:
            post = self.get_post (args[0])
            for trigger, action in self.triggers.items():
                if trigger.search(post['message']):
                    duration = time.time() - self.last_bot
                    self.last_bot = time.time()
                    print duration
                    if (duration > 10):
                        values = self.monsters[action['monster']].action(action['action'])
                        self.send_message(values["message"], values["picture"], values["fingerprint"])

    def run (self):
        """start the monsters!"""

        if self.debug:
            print "Listening to %s" % self.address

        with SocketIO(self.address) as socketIO_listen:
            socketIO_listen.on('message', self.on_message)
            socketIO_listen.wait()

if __name__ == '__main__':
    game = MeatMonsters()
    game.run()
