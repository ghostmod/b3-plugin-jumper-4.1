# Jumper Plugin for BigBrotherBot
# Copyright (C) 2012 Mr.Click
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# CHANGELOG
#
# 21/02/2012 (v1.0 Mr.Click)
#  * Initial version
#
# 12/03/2012 (v1.1 Mr.Click)
#  * Added demo auto recording
#
# 27/05/2012 (v1.2 Mr.Click)
#  * Added protection to stop recording from spectators
#  * Bugfixes and code cleanup
#
# 04/06/2012 (v1.3 Mr.Click)
#  * Added demo stop upon map change if the player was recording
#  * Some changes to in-game messages
#  * Removed non necessary verbose logging
#
# 26/08/2012 (v1.4 Mr.Click)
#  * Added automatic empty server handling


__author__ = 'Mr.Click - http://goreclan.net'
__version__ = '1.4'

import b3
import b3.plugin
import b3.events
import time
import re
from threading import Timer

class JumperPlugin(b3.plugin.Plugin):
    
    _adminPlugin = None
    _timer = None
    
    _SELECT_QUERY_PERSONAL_RECORD = "SELECT * FROM `maps_records` WHERE `client_id` = '%s' AND `map` = '%s'"
    _SELECT_QUERY_MAP_RECORD = "SELECT * FROM `maps_records` WHERE `map` = '%s' AND `time` < '%d'"
    _SELECT_QUERY_MAP_RECORD_COMPLEX = "SELECT * FROM `maps_records` WHERE `map` = '%s' AND `time` = (SELECT MIN(time) FROM `maps_records` WHERE `map` = '%s')"
    _SELECT_QUERY_CHECK_FIRST_RECORD = "SELECT * FROM `maps_records` WHERE `client_id` = '%s' AND `map` = '%s'"
    _INSERT_QUERY = "INSERT INTO `maps_records` (`client_id` , `map` , `time` , `time_add`) VALUES ('%s', '%s', '%d', '%d')"
    _UPDATE_QUERY = "UPDATE `maps_records` SET `time` = '%d', `time_add` = '%d' WHERE `client_id` = '%s' AND `map` = '%s'"
    _DELETE_QUERY = "DELETE FROM `maps_records` WHERE `client_id` = '%s' AND `map` = '%s'"


    def onStartup(self):
        """\
        Initialize plugin settings
        """
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:    
            self.error('Could not find admin plugin')
            return False
        
        #Register our commands
        if 'commands' in self.config.sections():
            for cmd in self.config.options('commands'):
                level = self.config.get('commands', cmd)
                sp = cmd.split('-')
                alias = None
                if len(sp) == 2: cmd, alias = sp

                func = self.getCmd(cmd)
                if func: self._adminPlugin.registerCommand(self, cmd, level, func, alias)
        
        #Register the events needed
        self.registerEvent(b3.events.EVT_GAME_WARMUP)
        self.registerEvent(b3.events.EVT_CLIENT_CONNECT)
        self.registerEvent(b3.events.EVT_CLIENT_DISCONNECT)
        
        #Creating necessary variables
        for client in self.console.clients.getList():
            client.setvar(self, 'start', None)
            client.setvar(self, 'stop', None)
            client.setvar(self, 'save', False)
            
            
    # ------------------------------------- Handle Events ------------------------------------- #        
        

    def onEvent(self, event):
        """\
        Handle intercepted events
        """
        if event.type == b3.events.EVT_GAME_WARMUP:
            self.onGameWarmup()     
        elif (event.type == b3.events.EVT_CLIENT_CONNECT):
            self.onClientConnect(event.client)      
        elif (event.type == b3.events.EVT_CLIENT_DISCONNECT):
            self.onClientDisconnect(event.client)
            
                
    # --------------------------------------- Functions --------------------------------------- #
        
        
    def getCmd(self, cmd):
        cmd = 'cmd_%s' % cmd
        if hasattr(self, cmd):
            func = getattr(self, cmd)
            return func
        return None    
    
    
    def onGameWarmup(self):
        """\
        Perform operations on map start
        """
        self._timer = None
        for client in self.console.clients.getList():
            # Checking if the player was recording
            if client.var(self, 'start').value != None and client.var(self, 'stop').value == None:
                # The guy was recording a jump time on previous map
                # Stopping the demo recording
                self.console.write('stopserverdemo %s' % client.cid)
                
            self.clearClientVars(client)
    
    
    def onClientConnect(self, client):
        """\
        Perform operations on client connect
        """
        self.clearClientVars(client)
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        
    
    def onClientDisconnect(self, client):
        """\
        Perform operations on client disconnect
        """
        if client.var(self, 'start').value != None and client.var(self, 'stop').value == None:
            # The guy was recording and quitted the game.
            # Server side demos are going to be stopped automatically. Just noticing here
            self.console.say('^7[^1DEMO^7] Stopped recording %s' % self.stripColors(client.name))
    
        self.clearClientVars(client)
        self.checkEmptyServer()
        
        
    def checkEmptyServer(self):
        """\
        If 0 players are online a timed thread will be lanuched to cycle the map
        """
        if self._timer is None:
            # We are not checking already
            if len(self.console.clients.getList()) == 0:
                # Starting routine
                self.debug('Starting routine to cycle current map if no one connect in 10 minutes.')
                self._timer = Timer(600, self.handleEmptyServer)
                self._timer.start()
    
    
    def handleEmptyServer(self):
        """\
        Cycle the current map if there are 0 players online
        """    
        if len(self.console.clients.getList()) == 0:
            self.debug('No players online. Cycling current map.')
            self.console.write('cyclemap')
        
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
                
                
    def clearClientVars(self, client):
        """\
        Restore client jump variables to default values
        """
        client.setvar(self, 'start', None)
        client.setvar(self, 'stop', None)
        client.setvar(self, 'save', False)
    
    
    def getHumanReadableTime(self, timestamp):
        """\
        Return a string representing the Human Readable time [min:sec]
        """
        minutes = timestamp / 60
        seconds = timestamp % 60
        if minutes < 10: minutes = '0' + str(minutes)
        else: minutes = str(minutes)
        if seconds < 10: seconds = '0' + str(seconds)
        else: seconds = str(seconds)
        return minutes + ':' + seconds
        
        
    def getHumanReadableDate(self, timestamp):
        """\
        Return a string representing the Human Readable date ['Thu, 28 Jun 2001']
        """
        gmtime = time.gmtime(timestamp)
        return time.strftime("%a, %d %b %Y", gmtime)
        
        
    def checkPersonalRecord(self, client): 
        """\
        Check if a player made a new personal record
        """
        cursor = self.console.storage.query(self._SELECT_QUERY_PERSONAL_RECORD % (client.id, self.console.game.mapName))
        
        if cursor.EOF:
            # No entries in maps_records DB table
            # So this is a new personal record
            cursor.close()
            return True
            
        row = cursor.getRow()
        oldTime = int(row['time'])
        newTime = client.var(self, 'stop').value - client.var(self, 'start').value
        cursor.close()
        
        if newTime < oldTime: 
            return True
        
        return False
       
       
    def checkNewMapRecord(self, client): 
        """\
        Check if a player made a new record for the current map
        """
        jumptime = client.var(self, 'stop').value - client.var(self, 'start').value
        cursor = self.console.storage.query(self._SELECT_QUERY_MAP_RECORD % (self.console.game.mapName, jumptime))
        
        if cursor.EOF: 
            cursor.close()
            return True
        
        cursor.close()
        return False
  
    
    def stripColors(self, s):
        """\
        Remove ioq3 color codes from a given string
        """
        sanitized = re.sub('\^[0-9]{1}','',s)
        return sanitized
         
         
    # --------------------------------------- Commands -----------------------------------------#            
    
    
    def cmd_jmpstart(self, data, client, cmd=None):
        """\
        Start the timer.
        """
        if not client.isvar(self, 'start') or not client.isvar(self, 'stop') or not client.isvar(self, 'save'):
            # Necessary variables has not been found for the current client
            # We can safely add them now and start the timer
            client.setvar(self, 'start', None)
            client.setvar(self, 'stop', None)
            client.setvar(self, 'save', False)
        
        if client.var(self, 'start').value != None and client.var(self, 'stop').value == None:
            # The timer has already been started
            client.message('^3The timer has already been started')
            return False
    
        if client.team == b3.TEAM_SPEC:
            # Cannot start the timer as a spectator
            client.message('^3You cannot start recording while being in spectator mode')
            return False
            
        client.setvar(self, 'start', int(time.time()))
        client.setvar(self, 'stop', None)
        client.setvar(self, 'save', False)
        
        # Starting the server side demo
        self.console.write('startserverdemo %s' % (client.cid))
        
        # Telling everyone that a server demo is being recorded
        client.message('^2Timer started')
        self.console.say('^7[^2DEMO^7] Started recording %s' % self.stripColors(client.name))
  
  
    def cmd_jmpstop(self, data, client, cmd=None):
        """\
        Stop the timer.
        """
        if not client.isvar(self, 'start') or not client.isvar(self, 'stop') or not client.isvar(self, 'save'):
            # Necessary variables has not been found for the current client
            # We can add them now but we are exiting the function since no start time has been tracked
            client.setvar(self, 'start', None)
            client.setvar(self, 'stop', None)
            client.setvar(self, 'save', False)    
            client.message('^3The timer has not been started')
            return False
                 
        if client.var(self, 'start').value == None:
            # The timer has not been started
            client.message('^3The timer has not been started')
            return False
        
        client.setvar(self, 'stop', int(time.time()))
        client.setvar(self, 'save', False)
        
        # Stopping the server side demo
        self.console.write('stopserverdemo %s' % (client.cid))
        
        # Telling everyone that a server demo stopped recording
        client.message('^1Timer stopped')
        self.console.say('^7[^1DEMO^7] Stopped recording %s' % self.stripColors(client.name))
        
        # Informing the client of his jump time
        jumptime = client.var(self, 'stop').value - client.var(self, 'start').value
        client.message('^3Time: ^2%s' % self.getHumanReadableTime(jumptime))
            
        # Checking new personal record for the current client
        # The map record will be checked once the player save it in the database
        if self.checkPersonalRecord(client):
            client.setvar(self, 'save', True)
            client.message('^3You established a new personal record on this map!')
            client.message('^3Type ^2!^3saverecord in chat to save it permanently') 
        else:
            client.setvar(self, 'save', False)
            client.message('^3No new personal record. Try again!')
        
        
    def cmd_jmpsaverecord(self, data, client, cmd=None):
        """\
        Saves the record established permanently
        """
        if client.var(self, 'save').value != True or client.var(self, 'start').value == None or client.var(self, 'stop').value == None:
            # The player didn't established a new personal record.
            # We can exit here since he need to establish a new record in order to use this command
            client.message('^3You need to establish a new record to save it permanently')
            return False
        
        # We need first to check if the player established a new map record
        # If we do it after the insert statement the query will fail everytime
        newMapRecord = False
        if self.checkNewMapRecord(client): 
            self.verbose('Player %s established a new record on map %s' % (self.stripColors(client.name), self.console.game.mapName))
            newMapRecord = True
        
        jumptime = client.var(self, 'stop').value - client.var(self, 'start').value
        cursor = self.console.storage.query(self._SELECT_QUERY_CHECK_FIRST_RECORD % (client.id, self.console.game.mapName))
        
        if cursor.EOF: 
            # New entry for this client on this map
            _query = self._INSERT_QUERY % (client.id, self.console.game.mapName, jumptime, int(time.time()))
        else: 
            # We already got an entry for this client on this map, performing an update
            _query = self._UPDATE_QUERY % (jumptime, int(time.time()), client.id, self.console.game.mapName)
       
        cursor.close()
        
        self.debug('Saving new personal record for player %s on map %s' % (self.stripColors(client.name), self.console.game.mapName))
        cursor = self.console.storage.query(_query)
        cursor.close()
        
        # Clearing client variables
        self.clearClientVars(client)
        
        client.message('^3Your record has been saved pemanently')
        if newMapRecord: self.console.write('bigtext ^7%s ^3established a new map record!' % (self.stripColors(client.name)))
    
    
    def cmd_jmpdelrecord(self, data, client, cmd=None):
        """\
        Delete your personal record for the current map
        """
        cursor = self.console.storage.query(self._SELECT_QUERY_PERSONAL_RECORD % (client.id, self.console.game.mapName))
        
        if cursor.EOF:
            # No entries in mapsrecords DB table for the current player, can't delete
            client.message('^3Your have no record saved. Can\'t delete')
            cursor.close()
            return
            
        cursor.close()
        cursor = self.console.storage.query(self._DELETE_QUERY % (client.id, self.console.game.mapName))
        cursor.close()
        self.verbose('%s\'s record on maps on map %s has been deleted' % (self.stripColors(client.name), self.console.game.mapName))
        client.message('^3Your record has been deleted')
        
    
    def cmd_jmprecord(self, data, client, cmd=None):
        """\
        [<name>] - Return the player record for current map
        """
        if not data:
            sclient = client
        else:
            sclient = self._adminPlugin.findClientPrompt(data, client)
            if not sclient: 
                # A client has not been found
                # The user will retry with a more specific name
                return False
            
        cursor = self.console.storage.query(self._SELECT_QUERY_PERSONAL_RECORD % (sclient.id, self.console.game.mapName))
        
        if cursor.EOF:
            # No entries in maps_records DB table for the specified player, can't display
            cmd.sayLoudOrPM(client, '^3No record found')
            cursor.close()
            return False
            
        row = cursor.getRow()
        jumptime = int(row['time'])
        timeadd = int(row['time_add'])
        cursor.close()
        
        cmd.sayLoudOrPM(client, '^3Record for ^7%s ^3on map ^4%s' % (self.stripColors(sclient.name), self.console.game.mapName))
        cmd.sayLoudOrPM(client, '^3Time: ^2%s ^3established on ^4%s' % (self.getHumanReadableTime(jumptime), self.getHumanReadableDate(timeadd)))
        
    
    def cmd_jmpmaprecord(self, data, client, cmd=None):
        """\
        Return the current map record
        """  
        cursor = self.console.storage.query(self._SELECT_QUERY_MAP_RECORD_COMPLEX % (self.console.game.mapName, self.console.game.mapName))
        
        if cursor.EOF:
            # No entries in maps_records DB table for the specified player, can't display
            cmd.sayLoudOrPM(client, '^3No record found')
            cursor.close()
            return False
            
        row = cursor.getRow()
        cid = '@' + str(row['client_id'])
        jumptime = int(row['time'])
        timeadd = int(row['time_add'])
        cursor.close()
        
        sclient = self._adminPlugin.findClientPrompt(cid, client)
        if not sclient: 
            # B3 was unable to find a client for the client_id specified
            # Exit here in order to prevent failures
            return False
            
        cmd.sayLoudOrPM(client, '^3Record for map ^4%s' % (self.console.game.mapName))
        cmd.sayLoudOrPM(client, '^3Player: ^7%s' % (self.stripColors(sclient.name)))
        cmd.sayLoudOrPM(client, '^3Time: ^2%s ^3established on ^4%s' % (self.getHumanReadableTime(jumptime), self.getHumanReadableDate(timeadd)))

