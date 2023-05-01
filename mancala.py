import time
import sys
import math
import board
import digitalio
import adafruit_character_lcd.character_lcd as characterlcd
from pitop import Pitop

miniscreen = Pitop().miniscreen
upButton = miniscreen.up_button
downButton = miniscreen.down_button
selectButton = miniscreen.select_button
cancelButton = miniscreen.cancel_button

lcd_columns = 20
lcd_rows = 4

# Raspberry Pi Pin Config:
lcd_rs = digitalio.DigitalInOut(board.D26)
lcd_en = digitalio.DigitalInOut(board.D19)
lcd_d7 = digitalio.DigitalInOut(board.D27)
lcd_d6 = digitalio.DigitalInOut(board.D22)
lcd_d5 = digitalio.DigitalInOut(board.D24)
lcd_d4 = digitalio.DigitalInOut(board.D25)
lcd_backlight = digitalio.DigitalInOut(board.D4)

# Initialise the lcd class
lcd = characterlcd.Character_LCD_Mono(
    lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7, lcd_columns, lcd_rows, lcd_backlight
)
gameOver = False


def toTwoDigits(num):
    if num == 0:
        return "00"
    if num < 10:
        return f"0{num}"
    return str(num)


class LcdMancalaBoard:
    player1Pits = [4, 4, 4, 4, 4, 4]
    player2Pits = [4, 4, 4, 4, 4, 4]
    player1Store = 0
    player2Store = 0
    currentPlayer = 1
    playerCursorIndex = 0
    lastNotification = ""

    def render(self):
        reversePlayer2Pits = self.player2Pits.copy()
        reversePlayer2Pits.reverse()
        return f""" {" ".join([toTwoDigits(x) for x in reversePlayer2Pits[:3]])}  {" ".join([toTwoDigits(x) for x in reversePlayer2Pits[3:]])}
{toTwoDigits(self.player2Store)}{" " * 16}{toTwoDigits(self.player1Store)}
 {" ".join([toTwoDigits(x) for x in self.player1Pits[:3]])}  {" ".join([toTwoDigits(x) for x in self.player1Pits[3:]])}"""

    def update_display(self):
        lcd.clear()
        lcd.cursor_position(0, 0)
        print(self.render() + f"\nPlayer {self.currentPlayer}'s turn")
        lcd.message = self.render() + f"\nPlayer {self.currentPlayer}'s turn"
        self.player_cursor_reset()

    def coordinates_of_player_pit(self, player: int, pit: int) -> tuple[int, int]:
        """Returns the coordinates of the rightmost rendered character of the player's nth pit.
        0-5: Player's pits
        """
        if player == 1:
            if pit < 3:
                return (pit * 3 + 2, 2)
            return (pit * 3 + 3, 2)
        else:
            if pit < 3:
                return (18 - pit * 3, 0)
            return (17 - pit * 3, 0)

    def player_cursor_next(self):
        self.playerCursorIndex = (self.playerCursorIndex + 1) % 6
        self.player_cursor_reset()

    def player_cursor_prev(self):
        self.playerCursorIndex = (self.playerCursorIndex - 1) % 6
        self.player_cursor_reset()

    def player_cursor_reset(self):
        lcd.cursor_position(
            *self.coordinates_of_player_pit(self.currentPlayer, self.playerCursorIndex))

    def player_selected_id(self):
        return self.playerCursorIndex + (0 if self.currentPlayer == 1 else 7)

    def coordinates_of_pit(self, pit: int):
        """Moves the lcd cursor to the rightmost rendered character of the pit with the given ID.
        Pits are ordered as follows:
        0-5: Player 1's pits
        6: Player 1's store
        7-12: Player 2's pits
        13: Player 2's store
        """
        if pit == 6:
            return (19, 1)
        if pit == 13:
            return (1, 1)
        player = 1 if pit < 7 else 2
        return self.coordinates_of_player_pit(player, pit if player == 1 else pit - 7)

    def cursor_to_space(self, pit: int):
        """Moves the lcd cursor to the rightmost rendered character of the pit with the given ID.
        Pits are ordered as follows:
        0-5: Player 1's pits
        6: Player 1's store
        7-12: Player 2's pits
        13: Player 2's store
        """
        lcd.cursor_position(*self.coordinates_of_pit(pit))

    def get_space_value(self, space: int):
        """Returns the number of stones in the specified space.
        Spaces are ordered as follows:
        0-5: Player 1's pits
        6: Player 1's store
        7-12: Player 2's pits
        13: Player 2's store
        """
        if space > 13 or space < 0:
            raise ValueError("Space must be between 0 and 13")
        if space == 6:
            return self.player1Store
        if space == 13:
            return self.player2Store
        if space < 7:
            return self.player1Pits[space]
        return self.player2Pits[space - 7]

    def set_space_value(self, space: int, value: int):
        """Sets the number of stones in the specified space.
        Spaces are ordered as follows:
        0-5: Player 1's pits
        6: Player 1's store
        7-12: Player 2's pits
        13: Player 2's store
        """
        if space > 13 or space < 0:
            raise ValueError("Space must be between 0 and 13")
        elif space == 6:
            self.player1Store = value
        elif space == 13:
            self.player2Store = value
        elif space < 7:
            self.player1Pits[space] = value
        else:
            self.player2Pits[space - 7] = value
        self.update_one_space(space)

    def add_to_space(self, space: int, value: int):
        """Adds the specified number of stones to the specified space.
        Spaces are ordered as follows:
        0-5: Player 1's pits
        6: Player 1's store
        7-12: Player 2's pits
        13: Player 2's store
        """
        self.set_space_value(space, self.get_space_value(space) + value)

    def update_one_space(self, space: int):
        """Replaces the characters of the specified space with the correct number of stones.
        Spaces are ordered as follows:
        0-5: Player 1's pits
        6: Player 1's store
        7-12: Player 2's pits
        13: Player 2's store
        """
        if space > 13 or space < 0:
            raise ValueError("Space must be between 0 and 13")
        rightmostCharacter = self.coordinates_of_pit(space)
        lcd.cursor_position(rightmostCharacter[0] - 1, rightmostCharacter[1])
        lcd.message = toTwoDigits(self.get_space_value(space))

    def switch_player(self):
        self.currentPlayer = 1 if self.currentPlayer == 2 else 2
        lcd.cursor_position(7, 4)
        lcd.message = f"{self.currentPlayer}"
        self.player_cursor_reset()

    def check_all_empty(self, player):
        if player == 1:
            return sum(self.player1Pits) == 0
        return sum(self.player2Pits) == 0

    def check_game_over(self):
        if self.check_all_empty(1) or self.check_all_empty(2):
            self.lcd_notification("Game over!")
            time.sleep(2)
            lcd.clear()
            lcd.message = f"Game over!\nScore {self.player2Store} - {self.player1Store}\n\nPlayer {2 if self.player2Store > self.player1Store else 1} wins!"
            sys.exit()

    def lcd_notification(self, message: str):
        if len(message) > 16:
            raise ValueError("Message must be 16 characters or less")
        if len(message) < len(self.lastNotification):
            lcd.cursor_position(math.floor(
                (16 - len(self.lastNotification)) / 2 + 2), 1)
            lcd.message = " " * len(self.lastNotification)

        lcd.cursor_position(math.floor((16 - len(message)) / 2 + 2), 1)
        lcd.message = message
        self.lastNotification = message
        print(message)

    def move_from_pit(self, player, pit) -> int:
        """Moves the stones from the given pit to the next pits, and returns the final pit.
        Pits are ordered as follows:
        0-5: Player 1's pits
        6: Player 1's store
        7-12: Player 2's pits
        13: Player 2's store
        """
        if pit > 13 or pit < 0 or pit == 6 or pit == 13:
            raise ValueError("Invalid pit")
        self.lcd_notification("")

        currentStones = self.get_space_value(pit)
        self.set_space_value(pit, 0)

        currentPitID = pit
        extraTurn = False
        steal = False
        while currentStones > 0:
            currentPitID = (currentPitID + 1) % 14
            if currentPitID == 6 or currentPitID == 13:
                if currentPitID == 6 and player == 1:
                    self.add_to_space(currentPitID, 1)
                    currentStones -= 1
                elif currentPitID == 13 and player == 2:
                    self.add_to_space(currentPitID, 1)
                    currentStones -= 1
            else:
                self.add_to_space(currentPitID, 1)
                currentStones -= 1

            if currentStones == 0 and self.get_space_value(currentPitID) == 1:
                if currentPitID < 6 and player == 1:
                    steal = True
                elif currentPitID > 6 and player == 2:
                    steal = True
            if currentStones == 0 and currentPitID == 6 and player == 1:
                extraTurn = True
            if currentStones == 0 and currentPitID == 13 and player == 2:
                extraTurn = True
        print(self.render())

        if extraTurn:
            self.lcd_notification("Extra turn!")
            return currentPitID

        if steal:
            self.lcd_notification("Steal!")
            self.set_space_value(currentPitID, 0)
            if player == 1:
                self.add_to_space(
                    6, self.get_space_value(12 - currentPitID) + 1)
                self.set_space_value(12 - currentPitID, 0)
            else:
                self.add_to_space(
                    13, self.get_space_value(12 - currentPitID) + 1)
                self.set_space_value(12 - currentPitID, 0)

        self.check_game_over()
        self.switch_player()
        return currentPitID


board = LcdMancalaBoard()
board.update_display()
lcd.cursor = True
lcd.blink = True

while True:
    upButton.when_pressed = board.player_cursor_next
    downButton.when_pressed = board.player_cursor_prev
    cancelButton.when_pressed = board.switch_player
    selectButton.when_pressed = lambda: board.move_from_pit(
        board.currentPlayer, board.player_selected_id())
