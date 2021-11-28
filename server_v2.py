import socket
import sys
import tiles
import threading
import random
import time

client_connection_list = [] # 所有正连接客户的数据连接通道
client_address_list = [] # 所有正连接的客户地址
client_idnum_list = [] # 所有正连接客户id
game_client_idnum = [] # 游戏中存货客户id
other_client_idnum = [] # 观众客户id
del_idnums = [] # 记录需要删除的客户的id
game_start_flag = 0 # 游戏开始标志
game_playing_flag = 0 # 游戏正在进行标志
eliminated_id_list = [] # 记录当局游戏已经淘汰客户的id
msg_history = [] # 记录历史信息（棋盘变化情况）
client_idnum_clear = [] # 记录已经断开连接的客户的id，在游戏结束从client_idnum_list将它清除

def client_handler(connection, address, idnum):
    host, port = address # 主机和端口
    name = '{}:{}'.format(host, port)  # 作为区分不同客户的标志

    # 创建数据接受的缓存区
    buffer = bytearray()
    
    prosess_flag = 1
    
    time_start = time.time()
    while prosess_flag:
        try:
            chunk = connection.recv(4096)
        except:
            # 该客户断开连接，记录进入待清理列表，游戏结束后一清除
            client_idnum_clear.append(idnum)
            
            # 客户断开连接后，直接淘汰
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
            # 该客户断开连接，记录进入待清理列表，游戏结束后一清除
            client_idnum_clear.append(idnum)
            
            # 客户断开连接后，直接淘汰
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
            # 读取游戏过程中客户发过来的消息
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
                                
                    # 如果该玩家gg，通知所有客户
                    for eliminated_id in eliminated:
                        if eliminated_id not in eliminated_id_list:
                            for i in range(len(game_client_idnum)):
                                try:
                                    client_connection_list[game_client_idnum[i]].send(tiles.MessagePlayerEliminated(eliminated_id).pack())
                                except:
                                    print("SB");
                            for i in range(len(other_client_idnum)):
                                try:
                                    client_connection_list[other_client_idnum[i]].send(tiles.MessagePlayerEliminated(eliminated_id).pack())
                                except:
                                    print("SB");
                            
                            msg_history.append(tiles.MessagePlayerEliminated(eliminated_id))
                            del_idnums.append(eliminated_id)
                            eliminated_id_list.append(eliminated_id)
                    
                    # pickup a new tile
                    tileid = tiles.get_random_tileid()
                    try:
                        connection.send(tiles.MessageAddTileToHand(tileid).pack())
                    except:
                        print("SB");
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
                                    print('SB')
                        
                        # 如果该玩家gg，通知所有客户
                        for eliminated_id in eliminated:
                            if eliminated_id not in eliminated_id_list:
                                for i in range(len(game_client_idnum)):
                                    try:
                                        client_connection_list[game_client_idnum[i]].send(tiles.MessagePlayerEliminated(eliminated_id).pack())
                                    except:
                                        print("SB");
                                for i in range(len(other_client_idnum)):
                                    try:
                                        client_connection_list[other_client_idnum[i]].send(tiles.MessagePlayerEliminated(eliminated_id).pack())
                                    except:
                                        print("SB");
                                msg_history.append(tiles.MessagePlayerEliminated(eliminated_id))
                                del_idnums.append(eliminated_id)
                                eliminated_id_list.append(eliminated_id)
                                
                        prosess_flag = 0

def client_listen(sock):
    while True:
        # 接受用户的连接
        connection, client_address = sock.accept()
        print('received connection from {}'.format(client_address))
        
        # 将新客户的连接和地址放进列表
        client_connection_list.append(connection)
        client_address_list.append(client_address)
        idnum = len(client_connection_list) - 1
        client_idnum_list.append(idnum)
        
        # 欢迎新连接的客户，并告知其id
        host, port = client_address_list[idnum] # 主机和端口
        name = '{}:{}'.format(host, port)  # 作为区分不同客户的标志
        try:
            client_connection_list[idnum].send(tiles.MessageWelcome(idnum).pack())
        except:
            print("SB");
        # 如果游戏已经开始，那么新加入的玩家都作为观众
        if game_playing_flag == 1:
            other_client_idnum.append(idnum)
            
            # 告知观众参与游戏的玩家
            print(game_client_idnum_init)
            for i in range(len(game_client_idnum_init)):
                game_play_id = game_client_idnum_init[i]
                h, p = client_address_list[game_client_idnum_init[i]]
                gam_play_name = '{}:{}'.format(h, p)
                try:
                    connection.send(tiles.MessagePlayerJoined(gam_play_name, game_play_id).pack())
                except:
                    print("SB")
            # 告知玩家游戏已经开始
            connection.send(tiles.MessageGameStart().pack())
            
            # 对用户更新当前棋盘情况
            for i in range(len(msg_history)):
                try:
                    connection.send(msg_history[i].pack())
                except:
                    print("SB")
                    
# 构建服务器端的TCP监听端口
# create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
# listen on all network interfaces
server_address = ('', 30020)
sock.bind(server_address)
print('listening on {}'.format(sock.getsockname()))
sock.listen(5)
sock.settimeout(10)

# 开启监听客户连接的子线程
t1 = threading.Thread(target = client_listen, args = [sock])
t1.start()

# 处理新一轮游戏
while True:
    # 对各个参数初始化
    game_start_flag = 0 # 清除游戏开始标志
    game_playing_flag = 0 # 清除游戏进行标志
    msg_history = [] # 清楚棋盘历史信息
    game_client_idnum = []
    other_client_idnum = []
    client_idnum_clear = []
    eliminated_id_list = []
    
    # 1.由用户数量决定是否开始游戏，如果人数大于1就等待30s，如果没有人加入就开始游戏；如果人数三人以上就立即开始游戏-------
    time_start = 0
    while True:
        if game_start_flag == 0:
            if len(client_idnum_list) > 1:
                game_start_flag = 1
                time_start = time.time() # 开始计时
        if game_start_flag == 1:
            time_end = time.time()
            if (time_end - time_start) > 10: # 计时超过30s
                print("Had wait:", time_end - time_start)
                break; # 跳出循环，游戏开始
        if len(client_idnum_list) > 3:
            break; # 跳出循环，游戏开始
    
    # 3s后游戏开始
    time_start = time.time() # 开始计时
    while True:
        if (time.time()-time_start) > 3:
            break
            
    # 2.游戏准备开始，首先从连接的用户中随机挑选参与游戏的客户，其他用户观战-----------------------------------------------
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
        host, port = client_address_list[idnum] # 主机和端口
        name = '{}:{}'.format(host, port)  # 作为区分不同客户的标志
        
        # 告知客户目前已经在游戏中的玩家
        for j in client_idnum_list:
            try:
                client_connection_list[j].send(tiles.MessagePlayerJoined(name, idnum).pack())
            except:
                print(j, " has left")
    # 3.游戏正式开始--------------------------------------------------------------------------------------------------------
    # 给每个玩家发送游戏开始的通知(此处假设客户不会断开连接)
    for i in range(len(game_client_idnum)):
        try:
            client_connection_list[game_client_idnum[i]].send(tiles.MessageGameStart().pack())
        except:
            print(i, " has left")
    # 给观战的客户发送游戏开始通知
    for i in range(len(other_client_idnum)):
        try:
            client_connection_list[other_client_idnum[i]].send(tiles.MessageGameStart().pack())
        except:
            print(i, " has left")

    # 为用户生成四个随机的块，并发给各个客户
    for j in range(len(game_client_idnum)):
        for _ in range(tiles.HAND_SIZE):
            tileid = tiles.get_random_tileid()
            try:
                client_connection_list[game_client_idnum[j]].send(tiles.MessageAddTileToHand(tileid).pack())
            except:
                print("SB");
            
    # 创建新的棋板
    board = tiles.Board()

    # 4.开始各个玩家的回合----------------------------------------------------------------------------------------------------
    while True:
        for i in range(len(game_client_idnum)):
            idnum = game_client_idnum[i]
            connection = client_connection_list[idnum]
            address = client_address_list[idnum]
            
            # 告诉该玩家你的回合已经到来，并对该玩家的信息进行处理
            for j in range(len(game_client_idnum)):
                try:
                    client_connection_list[game_client_idnum[j]].send(tiles.MessagePlayerTurn(idnum).pack())
                except:
                    client_idnum_clear.append(game_client_idnum[j])
            
            # 告诉观众，新的回合已经到来
            for j in range(len(other_client_idnum)):
                try:
                    client_connection_list[other_client_idnum[j]].send(tiles.MessagePlayerTurn(idnum).pack())
                except:
                    client_idnum_clear.append(other_client_idnum[j])
                    
            msg_history.append(tiles.MessagePlayerTurn(idnum))
            client_handler(connection, address, idnum)
        
        # 去除上一轮已经淘汰的用户
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
            
    # 5.清除已经断开的客户连接及地址--------------------------------------------------------------------------------------------
    client_idnum_clear = list(set(client_idnum_clear))
    for i in range(len(client_idnum_clear)):
        client_idnum_list.remove(client_idnum_clear[i])
        