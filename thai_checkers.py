import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QFrame, QPushButton, QHBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsItem, QAction, QDialog, QLabel
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QBrush, QPen, QColor, QIcon, QPixmap

CELL_SIZE = 80

class Board(QGraphicsView):
    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.scene.setSceneRect(0, 0, 8*CELL_SIZE, 8*CELL_SIZE) #limits of the scene
        self.scene.setBackgroundBrush(QBrush(QColor(135, 76, 28)))
        self.setFrameShape(QFrame.NoFrame)
        self.draw_board()
        
        self.game = Game()
        self.current_player = None
        self.active_pegs = []
        self.highlighted_cells = []
        self.init_pegs()
        
    def resizeEvent(self, event):
        margin = 50
        rect = self.scene.sceneRect().adjusted(-margin, -margin, margin, margin)
        self.fitInView(rect, Qt.KeepAspectRatio)
        super().resizeEvent(event)
        
    def draw_board(self):
        board_background = self.scene.addRect(0, 0, 8*CELL_SIZE, 8*CELL_SIZE, QPen(Qt.NoPen), QBrush(QColor(91, 58, 16)))
        board_background.setZValue(-2)
        pen = QPen(Qt.black, 5)
        for i in range(9):
            self.scene.addLine(i*CELL_SIZE, 0, i*CELL_SIZE, 8*CELL_SIZE, pen)
            
        for j in range(9):
            self.scene.addLine(0, j*CELL_SIZE, 8*CELL_SIZE, j*CELL_SIZE, pen)
        
    def add_peg(self, col, row, color):
        peg = Peg(col, row, color, self, self.game)
        self.scene.addItem(peg)
        self.active_pegs.append(peg)
        
    def init_pegs(self):
        for i in range(8):
            self.add_peg(i, 0, "w")
        for j in range(8):
            self.add_peg(j, 7, "b")
            
    def highlight_current_cell(self, col, row):
        brush = QBrush(QColor(169, 44, 30, 200))
        cell = self.scene.addRect(col*CELL_SIZE, row*CELL_SIZE, CELL_SIZE, CELL_SIZE, QPen(Qt.NoPen), brush)
        cell.setZValue(-1)
        self.highlighted_cells.append(cell)
            
    def highlight_moves(self, moves):
        for move in moves:
            col = move[0]
            row = move[1]
            brush = QBrush(QColor(121, 213, 98, 80))
            cell = self.scene.addRect(col*CELL_SIZE, row*CELL_SIZE, CELL_SIZE, CELL_SIZE, QPen(Qt.NoPen), brush)
            cell.setZValue(-1)
            self.highlighted_cells.append(cell)
            
    def clear_highlights(self):
        for cell in self.highlighted_cells:
            self.scene.removeItem(cell)
        self.highlighted_cells.clear()
        
    def enable_player_pegs(self, player_id):
        #makes all of the current player's pegs interactable
        self.current_player = player_id
        for peg in self.active_pegs:
            if peg.id == player_id:
                peg.enable()
            else:
                peg.disable()
                
    def delete_captured_pegs(self, captured_pegs):
        for peg in self.active_pegs:
            if [peg.col, peg.row] in captured_pegs:
                self.scene.removeItem(peg)
        self.active_pegs[:] = [peg for peg in self.active_pegs if [peg.col, peg.row] not in captured_pegs]
        
    def reset(self):
        for peg in self.active_pegs:
            self.scene.removeItem(peg)
        self.active_pegs.clear()
        self.init_pegs()
        
    def get_pegs(self):
        pegs_w = []
        pegs_b = []
        
        for peg in self.active_pegs:
            if peg.id == 1:
                pegs_w.append([peg.col, peg.row])
            else:
                pegs_b.append([peg.col, peg.row])
        
        return pegs_w, pegs_b
        

class Peg(QGraphicsItem):
    def __init__(self, col, row, color, parent_board, game):
        super().__init__()
        self.game = game
        self.parent_board = parent_board
        
        self.col = col
        self.row = row
        self.color = color
        self.id = 1 if self.color == "w" else 2
        
        self.disable()
        
        self.setPos(col*CELL_SIZE, row*CELL_SIZE)
        self.original_pos = [self.col, self.row]
        
    def boundingRect(self):
        return QRectF(0, 0, CELL_SIZE, CELL_SIZE) #area of interaction with the peg
    
    def paint(self, painter, option, widget):
        color = Qt.white if self.color == "w" else Qt.black
        painter.setPen(QPen(Qt.black, 4))
        painter.setBrush(QBrush(color))
        painter.drawEllipse(10, 10, CELL_SIZE - 20, CELL_SIZE - 20)
            
    def mousePressEvent(self, event):
        self.original_pos = [self.col, self.row]
        self.setZValue(1)                  #raise above other items in the scene
        self.parent_board.highlight_current_cell(self.col, self.row)
        moves = self.game.possible_move(self.col, self.row)
        self.parent_board.highlight_moves(moves)
        super().mousePressEvent(event)
        
    def mouseReleaseEvent(self, event):
        self.parent_board.clear_highlights()
        #makes sure peg snaps to a cell
        snap_col = round(self.x()/CELL_SIZE)
        snap_row = round(self.y()/CELL_SIZE)
        
        if self.game.is_valid_move(self.col, self.row, snap_col, snap_row):
            self.setPos(snap_col*CELL_SIZE, snap_row*CELL_SIZE)
            self.game.board[self.row][self.col] = 0
            self.col = snap_col
            self.row = snap_row
            self.game.board[self.row][self.col] = self.id
        else:
            self.setPos(self.col*CELL_SIZE, self.row*CELL_SIZE) #fall back to original position on invalid move
        self.setZValue(0)
        
        #check if actually moved
        if self.col != self.original_pos[0] or self.row != self.original_pos[1]:
            #handling capture
            captured_pegs = self.parent_board.game.check_capture(self.col, self.row, self.id)
            self.parent_board.delete_captured_pegs(captured_pegs)
            
            #handling labels update
            player_id = 2 if self.parent_board.current_player == 1 else 1
            self.parent_board.enable_player_pegs(player_id)
            self.parent_board.parent_window.update_turn_label(player_id)
            self.parent_board.game.num_moves += 1
            self.parent_board.parent_window.update_movecount_label()
            
            #checking for stalemate or win
            stalemate = self.parent_board.game.check_stalemate()
            if stalemate:
                self.parent_board.parent_window.display_stalemate_message()
            
            pegs_w, pegs_b = self.parent_board.get_pegs()   
            win, winner = self.parent_board.game.check_win(pegs_w, pegs_b)
            if win:
                self.parent_board.parent_window.display_win_message(winner)
        
        super().mouseReleaseEvent(event)
        
    def enable(self):
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setAcceptedMouseButtons(Qt.AllButtons)
        
    def disable(self):
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setAcceptedMouseButtons(Qt.NoButton)


class Game:
    def __init__(self):
        self.board = [[0]*8 for i in range(8)]
        self.board[0] = [1]*8
        self.board[7] = [2]*8               #1-white 2-black
        
        self.num_pegs_b = 8
        self.num_pegs_w = 8
        
        self.num_moves = 0
        
    def reset(self):
        self.board = [[0]*8 for i in range(8)]
        self.board[0] = [1]*8
        self.board[7] = [2]*8
        
        self.num_pegs_b = 8
        self.num_pegs_w = 8
        
        self.num_moves = 0
        
    def is_valid_move(self, col, row, new_col, new_row):
        #check within bounds
        if not (0 <= new_col <= 7 and 0 <= new_row <= 7):
            return False
        
        #check straight line
        if col != new_col and row != new_row:
            return False
        
        #check occupied
        if self.board[new_row][new_col] != 0:
            return False
        
        #check jump
        if col != new_col:
            step = 1 if new_col > col else -1
            for i in range(col+step, new_col, step):
                if self.board[row][i] != 0:
                    return False
        elif row != new_row:
            step = 1 if new_row > row else -1
            for j in range(row+step, new_row, step):
                if self.board[j][col] != 0:
                    return False
        return True
    
    def possible_move(self, col, row):
        moves = []
        
        #horizontal moves:
        #iterating left
        for i in range(col, -1, -1):
            if i != col:
                if self.board[row][i] == 0:
                    moves.append([i, row])
                else:
                    break
        #iterating right
        for i in range(col, 8, 1):
            if i != col:
                if self.board[row][i] == 0:
                    moves.append([i, row])
                else:
                    break
        #vertical moves:
        #iterating up
        for j in range(row, -1, -1):
            if j != row:
                if self.board[j][col] == 0:
                    moves.append([col, j])
                else:
                    break
        #iterating down
        for j in range(row, 8, 1):
            if j != row:
                if self.board[j][col] == 0:
                    moves.append([col, j])
                else:
                    break
        return moves
    
    def check_capture(self, col, row, peg_id):
        captured_pegs = []
        opponent_id = 2 if peg_id == 1 else 1
        #check in between capture
        #horizontally:
        #iterating left
        left = []
        for i in range(col, -1, -1):
            if self.board[row][i] != 0:
                left.append([self.board[row][i], i, row])
            else:
                break
        #iterating right
        right = []
        for i in range(col, 8, 1):
            if self.board[row][i] != 0:
                right.append([self.board[row][i], i, row])
            else:
                break
        #condition for capture:
        if any(record[0] == opponent_id for record in left) and any(record[0] == opponent_id for record in right):
            right[:] = [record[1:] for record in right if record[0] == opponent_id]
            left[:] = [record[1:] for record in left if record[0] == opponent_id]
            max_idx = min(len(left), len(right))
            for n in range(max_idx):
                if left[n] not in captured_pegs:
                    captured_pegs.append(left[n])
                if right[n] not in captured_pegs:
                    captured_pegs.append(right[n])
            
        #vertically
        #iterating up
        above = []
        for j in range(row, -1, -1):
            if self.board[j][col] != 0:
                above.append([self.board[j][col], col, j])
            else:
                break
        #iterating dowm
        bellow = []
        for j in range(row, 8, 1):
            if self.board[j][col] != 0:
                bellow.append([self.board[j][col], col, j])
            else:
                break
        #condition for capture
        if any(record[0] == opponent_id for record in above) and any(record[0] == opponent_id for record in bellow):
            above[:] = [record[1:] for record in above if record[0] == opponent_id]
            bellow[:] = [record[1:] for record in bellow if record[0] == opponent_id]
            max_idx = min(len(above), len(bellow))
            for n in range(max_idx):
                if above[n] not in captured_pegs:
                    captured_pegs.append(above[n])
                if bellow[n] not in captured_pegs:
                    captured_pegs.append(bellow[n])
        
        #check trap capture
        #horizontally:
        #iterating left
        count_friendly = 0
        left = []
        for i in range(col, -1, -1):
            if i != col:
                if self.board[row][i] == peg_id:
                    left.append([self.board[row][i], i, row])
                    count_friendly += 1
                    if count_friendly >= 1:
                        break
                elif self.board[row][i] == opponent_id:
                    left.append([self.board[row][i], i, row])
                else:
                    break
                
        if any(record[0] == opponent_id for record in left) and any(record[0] == peg_id for record in left):
            captured_pegs += [record[1:] for record in left if record[0] == opponent_id and record[1:] not in captured_pegs]
            
        #iterating right
        count_friendly = 0
        right = []
        for i in range(col, 8, 1):
            if i != col:
                if self.board[row][i] == peg_id:
                    right.append([self.board[row][i], i, row])
                    count_friendly += 1
                    if count_friendly >= 1:
                        break
                elif self.board[row][i] == opponent_id:
                    right.append([self.board[row][i], i, row])
                else:
                    break
        
        if any(record[0] == opponent_id for record in right) and any(record[0] == peg_id for record in right):
            captured_pegs += [record[1:] for record in right if record[0] == opponent_id and record[1:] not in captured_pegs]
            
        #vertically:
        #iterating up
        count_friendly
        above = []
        for j in range(row, -1, -1):
            if j != row:
                if self.board[j][col] == peg_id:
                    above.append([self.board[j][col], col, j])
                    count_friendly += 1
                    if count_friendly >= 1:
                        break
                elif self.board[j][col] == opponent_id:
                    above.append([self.board[j][col], col, j])
                else:
                    break
        
        if any(record[0] == opponent_id for record in above) and any(record[0] == peg_id for record in above):
            captured_pegs += [record[1:] for record in above if record[0] == opponent_id and record[1:] not in captured_pegs]
            
        #iterating down
        count_friendly
        bellow = []
        for j in range(row, 8, 1):
            if j != row:
                if self.board[j][col] == peg_id:
                    bellow.append([self.board[j][col], col, j])
                    count_friendly += 1
                    if count_friendly >= 1:
                        break
                elif self.board[j][col] == opponent_id:
                    bellow.append([self.board[j][col], col, j])
                else:
                    break
        
        if any(record[0] == opponent_id for record in bellow) and any(record[0] == peg_id for record in bellow):
            captured_pegs += [record[1:] for record in bellow if record[0] == opponent_id and record[1:] not in captured_pegs]
        
        for pos in captured_pegs:
            self.board[pos[1]][pos[0]] = 0
            if opponent_id == 1:
                self.num_pegs_w -= 1
            else:
                self.num_pegs_b -= 1
        return captured_pegs
    
    def check_win(self, pegs_w, pegs_b):
        if self.num_pegs_w == 0:
            return True, 2 #return boolean and the id of the winner
        elif self.num_pegs_b == 0:
            return True, 1
        
        moves_w = []
        moves_b = []
        
        for peg in pegs_w:
            moves_w.extend(self.possible_move(peg[0], peg[1]))
        for peg in pegs_b:
            moves_b.extend(self.possible_move(peg[0], peg[1]))
            
        if not moves_w:
            return True, 2
        if not moves_b:
            return True, 1
        
        return False, None
    
    def check_stalemate(self):
        if self.num_pegs_b == 1 and self.num_pegs_w == 1:
            return True
        return False



class StalemateDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Stalemate!")
        self.setStyleSheet("background-color: #4E2C0E")
        self.resize(200, 200)
        
        L_main = QVBoxLayout(self)
        
        T_stalemate = QLabel("Stalemate!")
        T_stalemate.setAlignment(Qt.AlignCenter)
        T_stalemate.setStyleSheet("""
                                  QLabel {
                                      color: #F5C89A;
                                      font-size: 20px;
                                      }""")
        
        L_main.addWidget(T_stalemate)


class WinDialog(QDialog):
    def __init__(self, parent, winner):
        super().__init__(parent)
        self.setWindowIcon(QIcon("trophy.png"))
        self.setWindowTitle("Win!")
        self.setStyleSheet("background-color: #4E2C0E")
        self.resize(200, 200)
        
        L_main = QVBoxLayout(self)
        
        self.L_trophy = QLabel()
        self.L_trophy.setAlignment(Qt.AlignCenter)
        self.trophy = QPixmap("trophy.png")
        self.L_trophy.setPixmap(self.trophy.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        T_win = QLabel(f"{winner} wins!")
        T_win.setAlignment(Qt.AlignCenter)
        T_win.setStyleSheet("""
                            QLabel {
                                color: #F5C89A;
                                font-size: 20px;
                                }""")
        
        L_main.addWidget(self.L_trophy)
        L_main.addWidget(T_win)
        
    def resizeEvent(self, event):
        trophy_scaled = self.trophy.scaled(self.L_trophy.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.L_trophy.setPixmap(trophy_scaled)
        super().resizeEvent(event)
        
        
class HowToPlayDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("How To Play Thai Checkers")
        self.setStyleSheet("background-color: #4E2C0E")
        self.resize(800, 500)
        
        L_main = QVBoxLayout(self)
        
        T_rules = QLabel()
        T_rules.setStyleSheet("""
                              QLabel {
                                  color: #F5C89A;
                                  font-size: 20px;
                                  }""")
        T_rules.setTextFormat(Qt.RichText)
        T_rules.setText("""
                        <u><b>Objective:</b></u> A player wins either by capturing all of the other opponent’s pegs or by <br>
                        trapping their opponent so that they do not have any legal moves left to make on their turn. <br>
                        Stalemate happens when both players only have one peg left. <br>
                        <u><b>Rules:</b></u>
                        First, players arrange all the pegs by colors in two opposite lines at the far ends of the 8x8 board. <br>
                        <b>Moving the Pegs:</b> Players can move forward, backward or sideways in a straight line, as many spots as they wish, as long as the way <br>
                        is not obstructed by another peg. You may not move diagonally. You may not "jump" over other pegs. <br>
                        <b>Taking Pegs Out:</b> Players can take out the opponent’s pegs in one of these two methods:
                        <ul>
                            <li>When a player manages to catch one or more of their opponent’s pegs by sandwiching the opponent’s peg(s) with two pegs <br>
                                along a line and there are no holes in the line, the sandwiched peg(s) are removed from the game.(see sketch #1). <br></li>
                            <li>When a player manages to put their peg(s) between the opponent's pegs in a line, and there are no holes in the line, the <br>
                                opponent's peg(s) are removed. <br>
                                If there is more than one peg on each side, remove an equal amount of pegs from both sides.</li>
                        </ul>""")
        L_main.addWidget(T_rules)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.board = Board(self)
        self.setWindowTitle("Thai Checkers Game")
        self.setStyleSheet("background-color: #874C1C;")
        self.make_ui()
        
    def make_ui(self):
        central_widget = QWidget()
        
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet("""
                               QMenuBar {
                                   background-color: #4E2C0E;
                                   color: #F5C89A;
                                   font-size: 22px;
                                   padding: 4px;
                                   }
                               QMenuBar::item {
                                   padding: 8px 16px;
                                   }
                               QMenuBar::item:selected {
                                   background-color: #63380F;
                                   }
                               QMenu {
                                   background-color: #4E2C0E;
                                   color: #F5C89A;
                                   font-size: 22px;
                                   padding: 4px;
                                   }
                               QMenu::item {
                                   padding: 8px 24px;
                                   }
                               QMenu::item:selected {
                                   background-color: #63380F;
                                   }""")
        
        M_info = menu_bar.addMenu("Help")
        
        A_howtoplay = QAction("How To Play", self)
        A_howtoplay.triggered.connect(self.open_how_to_play_dialog)
        M_info.addAction(A_howtoplay)
        
        L_main = QHBoxLayout()
        L_main.setContentsMargins(0,0,0,0)
        
        self.board.setMaximumWidth(960)
        L_main.addWidget(self.board)
        
        L_right = QVBoxLayout()
        L_right.setContentsMargins(0, 50, 20, 50)
        self.T_turn = QLabel("Waiting for new game")
        self.T_turn.setAlignment(Qt.AlignCenter)
        self.T_turn.setStyleSheet("""
                                  QLabel {
                                      background-color: #4E2C0E;
                                      color: #F5C89A;
                                      font-size: 30px;
                                      border-radius: 12px;
                                      padding: 14px 28px;}""")
        self.T_turn.setMaximumSize(400, 100)
        
        self.T_movecount = QLabel("0 Moves made")
        self.T_movecount.setAlignment(Qt.AlignCenter)
        self.T_movecount.setStyleSheet("""
                                       QLabel {
                                           background-color: #4E2C0E;
                                           color: #F5C89A;
                                           font-size: 30px;
                                           border-radius: 12px;
                                           padding: 14px 28px;}""")
        self.T_movecount.setMaximumSize(400, 100)
    
        self.B_start = QPushButton("Start Game")
        self.B_start.setStyleSheet("""
                                   QPushButton {
                                       background-color: #4E2C0E;
                                       color: #F5C89A;
                                       border-radius: 15px;
                                       padding: 8px 16px;
                                       font-size: 30px;
                                       }
                                   QPushButton:hover {
                                       background-color: #63380F;
                                       }
                                   QPushButton:pressed {
                                       background-color: #2E1A08;}""")
        self.B_start.setMaximumSize(400, 80)
        self.B_start.clicked.connect(self.start_game)
        
        spacer_label = QLabel()
        spacer_label.setMaximumHeight(150)
        L_right.addWidget(self.T_turn)
        L_right.addWidget(self.T_movecount)
        L_right.addWidget(spacer_label)
        L_right.addWidget(self.B_start)
        
        L_main.addLayout(L_right)
        central_widget.setLayout(L_main)
        self.setCentralWidget(central_widget)
        
    def open_how_to_play_dialog(self):
        dialog = HowToPlayDialog(self)
        dialog.exec_()
        
    def reset(self):
        self.board.game.reset()
        self.board.reset()
        
    def start_game(self):
        self.reset()
        
        self.board.enable_player_pegs(1)
        self.update_turn_label(1)
        self.update_movecount_label()
        
    def update_turn_label(self, player_id):
        if player_id == 1:
            text = "White's turn"
        else:
            text = "Black's turn"
        self.T_turn.setText(text)
        
    def update_movecount_label(self):
        self.T_movecount.setText(f"{self.board.game.num_moves} Moves made")
        
    def display_win_message(self, winner_id):
        winner = "White player" if winner_id == 1 else "Black player"
        dialog = WinDialog(self, winner)
        dialog.exec_()
        
    def display_stalemate_message(self):
        dialog = StalemateDialog(self)
        dialog.exec_()

        
if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec_())