
import socket
import sys
import tiles
import threading
import random
import time

client_connection_list = []
client_address_list = []
client_idnum_list = [] # all the ids that are connectted
game_client_idnum = []
other_client_idnum = [] # audience
del_idnums = []
game_start_flag = 0
game_playing_flag = 0
eliminated_id_list = []
msg_history = [] # record the board
client_idnum_clear = [] # ids that are disconected，eliminate them from client_idnum_list while game finished

def client_handler(connection, address, idnum):
    host, port = address
    name = '{}:{}'.format(host, port)

    # create buffer
    buffer = bytearray()
    
    prosess_flag = 1
    
    time_start = time.time()
    while prosess_flag:
        try:
            chunk = connection.recv(4096)
        except:
            # client disconnect, waitting to be eliminated after game finished
            client_idnum_clear.append(idnum)
            
            # if client disconnect, eliminated the player
            print('client {} disconnected'.format(address))
            for i in range(len(game_client_idnum)):
                try:
                    client_connection_list[game_client_idnum[i]].send(tiles.MessagePlayerEliminated(idnum).pack())
                except:
                    print("user error")
                    
            for i in range(len(other_client_idnum)):
                try:
                    client_connection_list[other_client_idnum[i]].send(tiles.MessagePlayerEliminated(idnum).pack())
                except:
                    print("user error")
            msg_history.append(tiles.MessagePlayerEliminated(idnum))
            del_idnums.append(idnum)
            return
            
        if not chunk:

            client_idnum_clear.append(idnum)
            

            print('client {} disconnected'.format(address))
            for i in range(len(game_client_idnum)):
                try:
                    client_connection_list[game_client_idnum[i]].send(tiles.MessagePlayerEliminated(idnum).pack())
                except:
                    print("user error")
            for i in range(len(other_client_idnum)):
                try:
                    client_connection_list[other_client_idnum[i]].send(tiles.MessagePlayerEliminated(idnum).pack())
                except:
                    print("user error")
            msg_history.append(tiles.MessagePlayerEliminated(idnum))
            del_idnums.append(idnum)
            return
        buffer.extend(chunk)
        
        while True:
            # read the msg
            msg, consumed = tiles.read_message_from_bytearray(buffer)
            if not consumed:
                break
            buffer = buffer[consumed:]

            print('received message {}'.format(msg))

            # sent by the player to put a tile onto the board (in all turns except
            # their second)
            if isinstance(msg, tiles.MessagePlaceTile):
                if board.set_tile(msg.x, msg.y, msg.tileid, msg.rotation, msg.idnum):
                    # notify client that placement was successful
                    msg_history.append(msg)
                    for i in client_idnum_list:
                        try:
                            client_connection_list[i].send(msg.pack())
                        except:
                            print(i, " has left")
                            
                    # check for token movement
                    positionupdates, eliminated = board.do_player_movement(game_client_idnum)
                    for msg in positionupdates:
                        msg_history.append(msg)
                        for i in client_idnum_list:
                            try:
                                client_connection_list[i].send(msg.pack())
                            except:
                                print(i, " has left")
                                
                    # If the player eliminated, notify all the others
                    for eliminated_id in eliminated:
                        if eliminated_id not in eliminated_id_list:
                            for i in range(len(game_client_idnum)):
                                try:
                                    client_connection_list[game_client_idnum[i]].send(tiles.MessagePlayerEliminated(eliminated_id).pack())
                                except:
                                    print("Error");
                            for i in range(len(other_client_idnum)):
                                try:
                                    client_connection_list[other_client_idnum[i]].send(tiles.MessagePlayerEliminated(eliminated_id).pack())
                                except:
                                    print("Error");
                            
                            msg_history.append(tiles.MessagePlayerEliminated(eliminated_id))
                            del_idnums.append(eliminated_id)
                            eliminated_id_list.append(eliminated_id)
                    
                    # pickup a new tile
                    tileid = tiles.get_random_tileid()
                    try:
                        connection.send(tiles.MessageAddTileToHand(tileid).pack())
                    except:
                        print("Error");
                    prosess_flag = 0

            # sent by the player in the second turn, to choose their token's
            # starting path
            elif isinstance(msg, tiles.MessageMoveToken):
                if not board.have_player_position(msg.idnum):
                    if board.set_player_start_position(msg.idnum, msg.x, msg.y, msg.position):
                        # check for token movement
                        positionupdates, eliminated = board.do_player_movement(game_client_idnum)
                        for msg in positionupdates:
                            msg_history.append(msg)
                            for i in client_idnum_list:
                                try:
                                    client_connection_list[i].send(msg.pack())
                                except:
                                    print('Error')
                        
                        # if this player eliminate, notify the others
                        for eliminated_id in eliminated:
                            if eliminated_id not in eliminated_id_list:
                                for i in range(len(game_client_idnum)):
                                    try:
                                        client_connection_list[game_client_idnum[i]].send(tiles.MessagePlayerEliminated(eliminated_id).pack())
                                    except:
                                        print("Error");
                                for i in range(len(other_client_idnum)):
                                    try:
                                        client_connection_list[other_client_idnum[i]].send(tiles.MessagePlayerEliminated(eliminated_id).pack())
                                    except:
                                        print("Error");
                                msg_history.append(tiles.MessagePlayerEliminated(eliminated_id))
                                del_idnums.append(eliminated_id)
                                eliminated_id_list.append(eliminated_id)
                                
                        prosess_flag = 0

def client_listen(sock):
    while True:
        # accept the connections
        connection, client_address = sock.accept()
        print('received connection from {}'.format(client_address))
        
        # put the connection to the connection list
        client_connection_list.append(connection)
        client_address_list.append(client_address)
        idnum = len(client_connection_list) - 1
        client_idnum_list.append(idnum)
        
        #  Welcome the new client, and tell the id
        host, port = client_address_list[idnum]
        name = '{}:{}'.format(host, port)
        try:
            client_connection_list[idnum].send(tiles.MessageWelcome(idnum).pack())
        except:
            print("Error");
        # If game already started, new clients that are connected will be the audience
        if game_playing_flag == 1:
            other_client_idnum.append(idnum)
            
            # Tell audience the players in the game
            print(game_client_idnum_init)
            for i in range(len(game_client_idnum_init)):
                game_play_id = game_client_idnum_init[i]
                h, p = client_address_list[game_client_idnum_init[i]]
                gam_play_name = '{}:{}'.format(h, p)
                try:
                    connection.send(tiles.MessagePlayerJoined(gam_play_name, game_play_id).pack())
                except:
                    print("Error")
            # messgage that game already started
            connection.send(tiles.MessageGameStart().pack())
            
            #  update the board
            for i in range(len(msg_history)):
                try:
                    connection.send(msg_history[i].pack())
                except:
                    print("Error")
                    

# create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
# listen on all network interfaces
server_address = ('', 30020)
sock.bind(server_address)
print('listening on {}'.format(sock.getsockname()))
sock.listen(5)

#  allow for multi connections
t1 = threading.Thread(target = client_listen, args = [sock])
t1.start()

# handle a new run
while True:
    #  initializte
    game_start_flag = 0
    game_playing_flag = 0
    msg_history = []
    game_client_idnum = []
    other_client_idnum = []
    client_idnum_clear = []
    eliminated_id_list = []

    # 1. base on number of player on when to start the game, one player would not start the game
    # if players < 3, wait for a second before start, if players >=3, start the game  -----
    time_start = 0
    while True:
        if game_start_flag == 0:
            if len(client_idnum_list) > 1:
                game_start_flag = 1
                time_start = time.time() #  count the time
        if game_start_flag == 1:
            time_end = time.time()
            if (time_end - time_start) > 3:
                print("Had wait:", time_end - time_start)
                break;
        if len(client_idnum_list) > 3:
            break;
    


    # 2. prepare the game, randomly chose the player from participants. other will be the audience ----
    print("The game begin!")
    game_client_idnum_init = []
    if len(client_idnum_list) < 5:
        game_client_idnum = client_idnum_list[:]
        game_client_idnum_init = game_client_idnum[:]
    else:
        idnum_shuffle = client_idnum_list[:]
        random.shuffle(idnum_shuffle)
        game_client_idnum = idnum_shuffle[0:4]
        other_client_idnum = idnum_shuffle[4:]
        game_client_idnum_init = game_client_idnum[:]
    print(game_client_idnum)
    print(other_client_idnum)

    game_playing_flag = 1 

    for i in range(len(game_client_idnum)):
        idnum = game_client_idnum[i]
        host, port = client_address_list[idnum]
        name = '{}:{}'.format(host, port)
        

        for j in client_idnum_list:
            try:
                client_connection_list[j].send(tiles.MessagePlayerJoined(name, idnum).pack())
            except:
                print(j, " has left")

    # 3. game start, notify all the player  ------
    for i in range(len(game_client_idnum)):
        try:
            client_connection_list[game_client_idnum[i]].send(tiles.MessageGameStart().pack())
        except:
            print(i, " has left")
    #  tell the audience
    for i in range(len(other_client_idnum)):
        try:
            client_connection_list[other_client_idnum[i]].send(tiles.MessageGameStart().pack())
        except:
            print(i, " has left")

    # generate the token for player
    for j in range(len(game_client_idnum)):
        for _ in range(tiles.HAND_SIZE):
            tileid = tiles.get_random_tileid()
            try:
                client_connection_list[game_client_idnum[j]].send(tiles.MessageAddTileToHand(tileid).pack())
            except:
                print("Error");

    board = tiles.Board()

    # 4.Roudn for each player---------------------------------------------------------------------------------------------------
    while True:
        for i in range(len(game_client_idnum)):
            idnum = game_client_idnum[i]
            connection = client_connection_list[idnum]
            address = client_address_list[idnum]

            # tell the player is your turn, and handle the information
            for j in range(len(game_client_idnum)):
                try:
                    client_connection_list[game_client_idnum[j]].send(tiles.MessagePlayerTurn(idnum).pack())
                except:
                    client_idnum_clear.append(game_client_idnum[j])
            
            # nofify the audience a new turn come
            for j in range(len(other_client_idnum)):
                try:
                    client_connection_list[other_client_idnum[j]].send(tiles.MessagePlayerTurn(idnum).pack())
                except:
                    client_idnum_clear.append(other_client_idnum[j])
                    
            msg_history.append(tiles.MessagePlayerTurn(idnum))
            client_handler(connection, address, idnum)
        

        # remove the players that are eliminated
        del_idnums = list(set(del_idnums))
        for i in range(len(del_idnums)):
            game_client_idnum.remove(del_idnums[i])
        del_idnums = []
        print(game_client_idnum)
        if len(game_client_idnum) < 2:
            time_start = time.time()
            while True:
                if (time.time() - time_start) > 10:
                    break
            break

    # 5. remove the clients that are disconneted
    client_idnum_clear = list(set(client_idnum_clear))
    for i in range(len(client_idnum_clear)):
        client_idnum_list.remove(client_idnum_clear[i])
        