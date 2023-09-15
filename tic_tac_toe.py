'''
How to run?

- Run this script as python3 tic_tac_toe.py playerid roomid. Replace playerid and roomid with your intended player and room ids respectively.
- You can also run this script without args. In that case you will be asked to enter the player and room id at runtime.
- Wait for your tun and set the mark.
- You can even drop out of the room and reconnect. The game would begin from where you left in that case.

'''

import redis_custom
import time
import sys

class Game:
    def __init__(self, playerid, roomid):
        self.__grid = [['-', '-', '-'], ['-', '-', '-'], ['-', '-', '-']]
        self.__redis_con = redis_custom.RedisCustom()
        
        if not self.__redis_con.is_connected():
            self.__in_room = False
            return

        self.__my_mark = '-'
        self.__my_player_id = playerid
        self.__room_id = roomid
        self.__last_played_by = ""
        self.__notification_channel = roomid + '_notification_channel'
        self.__players = ("", "")

        # remote game state is a string containing grid, who's turn it is
        remote_game_state = self.fetch_game_state()

        if remote_game_state == "":
            self.__last_played_by = self.__my_player_id
            self.__players = (self.__my_player_id, "")
            self.publish_game_state()
        else:
            grid, last_played_by, player1id, player2id = remote_game_state.split(",", 3)

            if player2id != "" and self.__my_player_id != player1id and self.__my_player_id != player2id:
                self.exit_room()
                return

            if player2id == "":
                player2id = self.__my_player_id

            self.__players = (player1id, player2id)
            self.__last_played_by = last_played_by
            self.set_grid_matrix(grid)

        if self.__players[0] == self.__players[1]:
            self.close_game()
            return

        if self.__my_player_id == self.__players[0]:
            self.__my_mark = 'o'
        else:
            self.__my_mark = 'x'

        self.__redis_con.subsribe(self.__notification_channel, self.notification_handler)
        self.__in_room = True
        return

    def pretty_grid(self):
        ret = ''
        ret += f' {self.__grid[0][0]} | {self.__grid[0][1]} | {self.__grid[0][2]} \r\n'
        ret += '---|---|---\r\n'
        ret += f' {self.__grid[1][0]} | {self.__grid[1][1]} | {self.__grid[1][2]} \r\n'
        ret += '---|---|---\r\n'
        ret += f' {self.__grid[2][0]} | {self.__grid[2][1]} | {self.__grid[2][2]} \r\n'
        return ret   

    def grid_box_hr(self):
        ret = ''
        for row in self.__grid:
            for col in row:
                ret += col
            ret += '\r\n'
        return ret

    def grid_string(self):
        return ''.join(self.grid_box_hr().split('\r\n'))
    
    def set_grid_matrix(self, grid):
        for i in range(3):
            for j in range(3):
                self.__grid[i][j] = grid[i*3 + j]

        return
    
    def close_game(self):
        self.exit_room()
        self.__redis_con.set(self.__room_id, "")
        return
    
    def exit_room(self):
        self.__in_room = False
        self.__redis_con.unsubscribe(self.__notification_channel)
        return

    def pass_turn(self):
        self.__last_played_by = self.__my_player_id
        return
    
    def mark(self, pos):
        i, j = pos
        if self.__grid[i][j] != '-':
            return False
        
        print("Setting mark at (%d, %d)" % pos)
        self.__grid[i][j] = self.__my_mark

        self.pass_turn()
        return True

    def check_winner(self):
        'return 1 if we win, 0 if the other person wins, -1 otherwise'
        winner_mark = '-'
        for i in range(3):            
            if self.__grid[0][i] == self.__grid[1][i] and self.__grid[1][i] == self.__grid[2][i] and self.__grid[0][i] != '-':
                winner_mark = self.__grid[0][i]
                break
        
        for i in range(3):
            if self.__grid[i][0] == self.__grid[i][1] and self.__grid[i][1] == self.__grid[i][2] and self.__grid[i][0] != '-':
                winner_mark = self.__grid[i][0]
                break

        if self.__grid[0][0] == self.__grid[1][1] and self.__grid[1][1] == self.__grid[2][2] and self.__grid[1][1] != '-':
                winner_mark = self.__grid[1][1]

        if self.__grid[0][2] == self.__grid[1][1] and self.__grid[1][1] == self.__grid[2][0] and self.__grid[1][1] != '-':
                winner_mark = self.__grid[1][1]

        if winner_mark == '-':
            return -1
        elif winner_mark == self.__my_mark:
            print("You won")
            return 1
        
        print("You lost")
        return 0
    
    def notification_handler(self, message):
        #  print(message)
        _, publisher, _ = message.split("--", 2)
        if publisher == self.__my_player_id:
            return

        # we should check new state
        remote_game_state = self.fetch_game_state()

        if remote_game_state == "":
            self.exit_room()
            return

        grid, last_played_by, player1id, player2id = remote_game_state.split(",", 3)
        self.set_grid_matrix(grid)
        self.__players = (player1id, player2id)

        if self.check_winner() != -1:
            self.close_game()
            return

        self.__last_played_by = last_played_by

    
    def fetch_game_state(self):
        remote_game_state = self.__redis_con.get(self.__room_id)
        return remote_game_state
    
    def publish_game_state(self):
        local_game_state = self.grid_string() + ',' + self.__last_played_by + ',' + self.__players[0] + ',' + self.__players[1]
        self.__redis_con.set(self.__room_id, local_game_state)
        print("Sent game state to remote")
        self.notify()
        return
    
    def notify(self):
        message = "Player --" +str(self.__my_player_id) + "-- published something"
        self.__redis_con.publish(self.__notification_channel, message)
        return
    
    def my_turn(self):
        return self.__my_player_id != self.__last_played_by
    
    def get_my_mark(self):
        return self.__my_mark
    
    def in_room(self):
        return self.__in_room

def ask_pos():
    print("Enter position to set mark (0-indexed):")
    i, j = -1, -1
    while i < 0 or i > 2:
            i = int(input("- i ([0,2] allowed):"))

    while j < 0 or j > 2:
            j = int(input("- j ([0,2] allowed):"))

    return i, j

if __name__ == '__main__':
    playerid = None
    roomid = None

    if sys.argv.__len__() > 1:
        if sys.argv[1].find("--") != -1:
            print("Invalid player id. Can't use '--' in player id")
        else:
            playerid = sys.argv[1]

    if playerid is None:
        playerid = input("Choose player id:")

    if sys.argv.__len__() > 2:
        roomid = sys.argv[2]


    if roomid is None:
        roomid = input("Choose room id:")

    game = Game(playerid, roomid)
    time.sleep(1)

    if game.in_room():
        print("Entered game room -> %s" % roomid)
        print("My mark -> '%s'" % game.get_my_mark())
        print(game.pretty_grid())

    while True:
        if not game.in_room():
            break

        if game.my_turn():
            print(game.pretty_grid())
            print("Your turn")
            i, j = ask_pos()
            game.mark((i, j))
            game.publish_game_state()
            print(game.pretty_grid())

            if game.check_winner() != -1:
                game.exit_room()

    print("Game over")