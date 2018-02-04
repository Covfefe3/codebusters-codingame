import sys
from math import sin, cos, sqrt, radians

busters_per_player = int(input())  # the amount of busters you control
ghost_count = int(input())  # the amount of ghosts on the map
my_team_id = int(input())  # if this is 0, your base is on the top left of the map, if it is one, on the bottom right

# round counter
currRound = 0

# list to keep fields scouted by busters
# true for visited, false for not visited
fieldH, fieldW = 90, 160
checkedFields = [False for i in range(0, fieldW * fieldH)]
for i in range(0, 9):
    checkedFields[(i // 3) * fieldW + (i % 3)] = True

# base position
if (my_team_id == 0):
    base = (0, 0)
    enemyBase = (16000, 9000)
else:
    base = (16000, 9000)
    enemyBase = (0, 0)


# return distance in euclidian coord
def distance(x1, y1, x2, y2):
    return sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


# CLASSES
# ***********************************************************************************************

# entity class, it will be inherited by busters and ghosts classes
class Entity:
    # pre-turn information got from stream
    def init_turn(self, _x, _y, _id, _state, _value):
        self.x = _x
        self.y = _y
        self.id = _id
        self.state = _state
        self.value = _value

    # returns tuple of coord where entity will be heading
    def head_to_point(self, x, y, dist):
        r = distance(self.x, self.y, x, y)
        # zero division error
        if (r == 0):
            r = 1
        Sin = (y - self.y) / r
        Cos = (x - self.x) / r
        newX = dist * Cos + self.x
        newY = dist * Sin + self.y
        return (int(newX), int(newY))


# my buster class, inherits from Entity
class myBuster(Entity):
    def __init__(self):
        # buster current command
        self.command = ""

        # in which round last stun has been used
        self.lastStun = -20

        # info about targeted ghost
        self.ghostId = -1

        # information if ghost was ejected and what's his id
        # make use of that information in next round after throwing ghost
        self.ejectedGhost = -1

    # BUSTER ABILITIES (which were listened in project information)
    def move(self, x, y):
        self.command = "MOVE " + str(x) + " " + str(y)

    # true if stun is ready
    def isStunOn(self):
        global currRound
        return currRound - self.lastStun >= 20

    # use stun
    def stun(self, enemyId):
        global currRound
        self.command = "STUN " + str(enemyId)
        self.lastStun = currRound

    # radar
    def radar(self):
        self.command = "RADAR"

    # release carried ghost
    def release(self):
        self.command = "RELEASE " + str(self.value)

    # trap ghost
    def bust(self, ghostId):
        self.command = "BUST " + str(ghostId)

    # eject carried ghost
    def eject(self, x, y):
        self.command = "EJECT " + str(x) + " " + str(y)

    # END OF ABILITIES

    # scout area, ghost will be heading to a nearest unvisited field
    def scout(self):
        global enemyBase, fieldW, fieldH, checkedFields
        minDist = (enemyBase[0], enemyBase[1], 20000)
        # find min distance
        for i in range(0, fieldH):
            for j in range(0, fieldW):
                if (checkedFields[i * fieldW + j] == False):
                    dist = distance(self.x, self.y, j * 100, i * 100)
                    if (dist < minDist[2]):
                        minDist = (j * 100, i * 100, dist)
        pos = self.head_to_point(minDist[0], minDist[1], 800)
        self.move(pos[0], pos[1])


# ghosts class
class ghost(Entity):
    def __init__(self):
        # whether the ghost is visible on radar in current round
        self.visible = True


# ***********************************************************************************************

# main class with game's logic
class gameLogic:
    # global busters_per_player, currRound, checkedFields, fieldW, fieldH, base, enemyBase
    def __init__(self):
        global busters_per_player
        # instances of classes
        self.busters = [myBuster() for i in range(0, busters_per_player)]
        self.enemy = []
        self.ghosts = []

        # whether or not busters can bust ghost with stanima>15
        self.heavyGhostsEnabled = False
        self.ghostsInBase = 0

        # last seen enemies position
        self.lastSeenEnemy = []

        # after game started radar will be used after 7 buster moves
        self.radarSteps = 7

        # list with enemies to neutralise, I want to take over their ghosts
        self.attack = []

    # count enemies in given range
    def count_enemies(self, x, y, range):
        counter = 0
        for v in self.enemy:
            counter += (distance(x, y, v.x, v.y) <= range)
        return counter

    # return ghost position in list
    def ghost_index(self, _id):
        k = 0
        while (k < len(self.ghosts) and self.ghosts[k].id != _id):
            k += 1
        if (k == len(self.ghosts)):
            # not found in list
            return -1
        return k

    # go to next turn
    def next_round(self):
        global currRound, ghost_count
        currRound += 1
        # resets enemylist
        self.enemy = []
        # marking all ghosts as invisible on radar
        for i in range(0, len(self.ghosts)):
            self.ghosts[i].visible = False

        # whether I can or can't start bust ghosts with less than 16 stanima points
        if (len(self.ghosts) + self.ghostsInBase >= ghost_count / 2):
            self.heavyGhostsEnabled = True

    # mark fields visited by my busters in every round
    def mark_visited_fields(self):
        global checkedFields, fieldW, fieldH
        for v in self.busters:
            for i in range(v.y // 100 - 22, v.y // 100 + 23):
                for j in range(v.x // 100 - 22, v.x // 100 + 23):
                    if (i >= 0 and i < fieldH and j >= 0 and j < fieldW):
                        if (distance(v.x, v.y, j * 100, i * 100) <= 2200):
                            # mark all points around buster in range 2200 as visited
                            checkedFields[i * fieldW + j] = True

    # update lastSeenEnemy list
    def update_last_seen_enemy(self):
        for i in range(0, len(self.lastSeenEnemy)):
            for vj in self.busters:
                if (distance(vj.x, vj.y, self.lastSeenEnemy[i][0], self.lastSeenEnemy[i][1]) <= 1800):
                    self.lastSeenEnemy[i] = (-10000, -10000, self.lastSeenEnemy[i][2])
        for v in self.enemy:
            i = 0
            while (i < len(self.lastSeenEnemy) and self.lastSeenEnemy[i][2] != v.id):
                i += 1
            if (i == len(self.lastSeenEnemy)):
                self.lastSeenEnemy.append((v.x, v.y, v.id))
            else:
                self.lastSeenEnemy[i] = (v.x, v.y, v.id)

    # deletes ghost which werent at last seen position from list --> it could be that enemy already busted him
    def del_fake_ghosts(self):
        for i in range(0, len(self.busters)):
            for j in range(len(self.ghosts) - 1, -1, -1):
                # if ghost isn't visible on radar and it's in range of buster seeing then delete it from list
                if (self.ghosts[j].visible == False and distance(self.ghosts[j].x, self.ghosts[j].y,
                                                                 self.busters[i].x, self.busters[i].y) <= 1780):
                    del self.ghosts[j]

    # going with ghost to the base and realising it
    def save_ghost(self):
        global base
        for i, v in enumerate(self.busters):
            if (v.state == 1):
                # buster is carrying ghost
                dist = distance(v.x, v.y, base[0], base[1])
                if (dist <= 1600):
                    # if buster is in range of dropping ghost in the base
                    self.busters[i].release()
                    self.ghostsInBase += 1
                else:
                    # move straight towards the base
                    pos = v.head_to_point(base[0], base[1], min(dist - 1600 + 5, 800))
                    self.busters[i].move(pos[0], pos[1])

    # choosing ghosts as targets to busters(buster can bust only that ghost whose id is equal to myBuster.ghostId)
    def choose_targeted_ghost(self):
        global ghost_count
        if (len(self.ghosts)):
            # if list is not empty
            for i in range(0, len(self.busters)):
                if (self.busters[i].state != 1 and self.busters[i].state != 2):
                    # buster isn't stunned and isn't carrying a ghost

                    # list with busters index, state, distance from ghost
                    temp = [[j, self.ghosts[j].state,
                             distance(self.busters[i].x, self.busters[i].y, self.ghosts[j].x, self.ghosts[j].y)] for j
                            in range(0, len(self.ghosts))]

                    # don't go for ghost with stanima<900 first it there are ghosts with stanima=0
                    for p in range(0, len(temp)):
                        if (temp[p][2] < 900):
                            temp[p][2] = 1770

                    # choose ghost with min stanima and distance
                    target = min(temp, key=lambda x: (x[1], x[2]))

                    if (target[1] <= 15 or (target[1] > 15 and self.heavyGhostsEnabled)):
                        # return true distance in case distance<900
                        target[2] = distance(self.busters[i].x, self.busters[i].y, self.ghosts[target[0]].x,
                                             self.ghosts[target[0]].y)
                        self.busters[i].ghostId = self.ghosts[target[0]].id

                        if (target[2] > 900):
                            pos = self.busters[i].head_to_point(self.ghosts[target[0]].x, self.ghosts[target[0]].y,
                                                                min(800, target[2] - 900))
                        else:
                            pos = self.busters[i].head_to_point(base[0], base[1], 800)
                        self.busters[i].move(pos[0], pos[1])

    # trap targeted ghost if it's in range
    def bust_ghost(self):
        for i in range(0, len(self.busters)):
            for v in self.ghosts:
                if (v.id == self.busters[i].ghostId):
                    # if buster is targeting that ghost
                    dist = distance(v.x, v.y, self.busters[i].x, self.busters[i].y)
                    if (dist >= 900 and dist <= 1760):
                        # in range
                        self.busters[i].bust(v.id)
                    break

    # busters stun enemies
    def stuning_system(self):
        global base
        # list with info about how many turns enemy will be stunned
        stunned = []
        for v in self.enemy:
            if (v.state == 2):
                # enemy is stunned
                stunned.append(v.value)
            else:
                # enemy not stunned --> 0 rounds
                stunned.append(0)

        # stunning enemies carrying ghosts
        for index, v in enumerate(self.enemy):
            if (v.state == 1):
                # enemy is carrying ghost
                for i in range(0, len(self.busters)):
                    if (self.busters[i].isStunOn() and self.busters[i].state != 2 and distance(self.busters[i].x,
                                                                                               self.busters[i].y, v.x,
                                                                                               v.y) <= 1760):
                        # if enemy is in range, stun him
                        stunned[index] = 10
                        self.busters[i].stun(v.id)
                        break

        # stunning enemies around buster trying to trap(targeting) or carrying ghost
        for v in self.busters:
            if (v.state == 1):
                # carrying ghost
                for j in range(0, len(self.enemy)):
                    dist = distance(v.x, v.y, self.enemy[j].x, self.enemy[j].y)
                    if (dist <= 2200 and stunned[j] <= 1):
                        # if enemy is nearby my buster
                        for k in range(0, len(self.busters)):
                            # go through list of my busters and choose one who will stun enemy
                            dist = distance(self.busters[k].x, self.busters[k].y, self.enemy[j].x, self.enemy[j].y)
                            if (self.busters[k].state != 2 and self.busters[k].isStunOn() and dist <= 1760):
                                self.busters[k].stun(self.enemy[j].id)
                                stunned[j] = 10
                                break
            else:
                # buster is targeting a ghost
                # checking for visibilyty of ghost whom my buster is targeting
                k = self.ghost_index(v.ghostId)
                if (k != -1 and self.ghosts[k].visible):
                    counter = 0
                    # counting my busters nearby that ghost
                    for l in self.busters:
                        if (distance(self.ghosts[k].x, self.ghosts[k].y, l.x, l.y) <= 2200):
                            counter += 1

                    if (counter * 9 >= self.ghosts[k].state):
                        # checking if in 9 rounds I will be able to take that ghost
                        for index, p in enumerate(self.enemy):
                            if (distance(self.ghosts[k].x, self.ghosts[k].y, p.x, p.y) <= 2200):
                                # if enemy is nearby that ghost -->try stunning him
                                for j in range(0, len(self.busters)):
                                    if (distance(self.busters[j].x, self.busters[j].y, p.x, p.y) <= 1760):
                                        if (self.busters[j].isStunOn() and stunned[index] <= 1 and self.busters[
                                            j].state != 2):
                                            self.busters[j].stun(p.id)
                                            stunned[index] = 10
                                            break

        if (len(self.ghosts) == 0):
            # there is no ghost in list  --> stun everything what's moving
            for index, p in enumerate(self.enemy):
                for j in range(0, len(self.busters)):
                    if (distance(self.busters[j].x, self.busters[j].y, p.x, p.y) <= 1760):
                        if (self.busters[j].isStunOn() and stunned[index] <= 1 and self.busters[j].state != 2):
                            self.busters[j].stun(p.id)
                            stunned[index] = 10
                            break

    # try to eject ghost
    def throw_ghost(self):
        global base
        # list with busters indexes
        sortBusters = [i for i in range(0, len(self.busters))]
        # sort busters by distance from base
        sortBusters.sort(key=lambda v: distance(self.busters[v].x, self.busters[v].y, base[0], base[1]))

        for i, vi in enumerate(self.busters):
            if (vi.state == 1 and self.count_enemies(vi.x, vi.y, 1760) == 0):
                # buster is carrying ghost
                for vj in sortBusters:
                    if ((base == (0, 0) and self.busters[vj].x >= vi.x) or (
                            base == (16000, 9000) and self.busters[vj].x <= vi.x)):
                        break
                    elif (self.busters[vj].ejectedGhost == -1 and self.busters[vj].state != 1 and self.busters[
                        vj].state != 2):
                        if (distance(vi.x, vi.y, self.busters[vj].x, self.busters[vj].y) >= 1760 + 100):
                            ghostPos = vi.head_to_point(self.busters[vj].x, self.busters[vj].y, 1760)
                            dist = distance(ghostPos[0], ghostPos[1], self.busters[vj].x, self.busters[vj].y)
                            receiverPos = (-1000, -1000)

                            if (dist > 100 and dist <= 1760):
                                receiverPos = self.busters[vj].head_to_point(ghostPos[0], ghostPos[1],
                                                                             -min(800, 1760 - dist - 2))
                            elif (dist > 1760 and dist < 1760 + 800):
                                receiverPos = self.busters[vj].head_to_point(ghostPos[0], ghostPos[1], dist - 1760 + 2)

                            if (receiverPos != (-1000, -1000)):
                                # checking for enemies nearby
                                if (self.count_enemies(self.busters[vj].x, self.busters[vj].y,
                                                       1760) == 0 and self.count_enemies(receiverPos[0],
                                                                                         receiverPos[1],
                                                                                         1760) == 0
                                    and self.count_enemies(ghostPos[0], ghostPos[1], 1760) == 0):
                                    # eject
                                    self.busters[vj].ejectedGhost = vi.value
                                    self.busters[vj].move(receiverPos[0], receiverPos[1])
                                    self.busters[i].eject(ghostPos[0], ghostPos[1])

                                    # checking if ejecting buster didn't use stun in this round
                                    if (vi.lastStun == currRound):
                                        # reset stun
                                        self.busters[i].lastStun = -20
                                    break

    # delete ghosts which will be caught after ejected(that ghosts should be visible only for receivers)
    def delete_ejected(self):
        for v in self.busters:
            if (v.ejectedGhost != -1):
                # ghost was threw to buster
                # find ghost position in list
                index = self.ghost_index(v.ejectedGhost)
                dist = distance(v.x, v.y, self.ghosts[index].x, self.ghosts[index].y)
                if (v.state != 2 and self.count_enemies(v.x, v.y, 1760) == 0 and dist >= 900 and dist <= 1760):
                    # buster will catch ghost --> delete ghost
                    del self.ghosts[index]

    def catch_ghost(self):
        for i, vi in enumerate(self.busters):
            if (vi.ejectedGhost != -1):
                # ghost was threw to buster
                index = self.ghost_index(vi.ejectedGhost)
                if (index == -1):  # index out of range --> index=-1
                    # buster will catch ghost(cause ghost was deleted from list)
                    self.busters[i].ghostId = vi.ejectedGhost
                    self.busters[i].bust(vi.ejectedGhost)
                self.busters[i].ejectedGhost = -1

    # using radar
    def radar(self):
        y = 4500
        if (self.radarSteps > 0):
            for i in range(0, len(self.busters)):
                self.busters[i].move(8000, y + ((-1) ** i) * i * 2500)
                y += ((-1) ** i) * i * 2500

            self.radarSteps -= 1
        elif (self.radarSteps == 0):
            # use radar
            for i in range(0, len(self.busters)):
                self.busters[i].radar()
            self.radarSteps -= 1

    # follow enemy who is carrying a ghost, try to take over his ghost
    def attack_enemy(self):
        global enemyBase
        for v in self.enemy:
            if (v.state == 1):
                j = 0
                while (j < len(self.attack) and self.attack[j][2] != v.id):
                    j += 1
                if (j == len(self.attack)):
                    # add new enemy
                    self.attack.append((v.x, v.y, v.id))
                else:
                    # update
                    self.attack[j] = (v.x, v.y, v.id)

        # removing enemies who lost ghost
        toDelete = []
        for i in range(0, len(self.attack)):
            for v in self.enemy:
                if (v.id == self.attack[i][2] and v.state != 1):
                    toDelete.append(i)
        for i in range(len(toDelete) - 1, -1, -1):
            del self.attack[toDelete[i]]
        toDelete = []

        for i, v in enumerate(self.attack):
            visible, going = False, False
            k = 0
            while (k < len(self.enemy) and self.enemy[k].id != v[2]):
                k += 1
            if (k < len(self.enemy)):
                visible = True

            for j in range(0, len(self.busters)):
                dist = distance(v[0], v[1], self.busters[j].x, self.busters[j].y)
                if (dist <= 2200 and visible):
                    # in visible range
                    if (distance(enemyBase[0], enemyBase[1], self.busters[j].x, self.busters[j].y) - 1760 <= distance(
                            enemyBase[0], enemyBase[1], v[0], v[1])):
                        if (self.busters[j].state != 1 and self.busters[j].state != 2):
                            self.busters[j].move(v[0], v[1])
                            going = True
                elif (dist <= 1500 and visible == False):
                    # to delete
                    going = False
                    break
                elif (self.busters[j].state != 1 and self.busters[j].state != 2):
                    # not in visible range
                    me, target = Entity(), Entity()
                    target.x, target.y = v[0], v[1]
                    turns = 0
                    while (True):
                        pos = target.head_to_point(enemyBase[0], enemyBase[1], 800)
                        target.x, target.y = pos[0], pos[1]
                        turns += 1

                        me.x, me.y = self.busters[j].x, self.busters[j].y
                        pos = me.head_to_point(target.x, target.y, 800 * turns)
                        me.x, me.y = pos[0], pos[1]

                        if (distance(target.x, target.y, enemyBase[0], enemyBase[1]) <= 1600):
                            break
                        elif (distance(me.x, me.y, target.x, target.y) <= 1760):
                            self.busters[j].move(target.x, target.y)
                            going = True
                            break

            if (going):
                # change position
                target = Entity()
                target.x, target.y = v[0], v[1]
                pos = target.head_to_point(enemyBase[0], enemyBase[1], 800)
                self.attack[i] = (pos[0], pos[1], v[2])
            else:
                toDelete.append(i)

        # deleting from list
        for i in range(len(toDelete) - 1, -1, -1):
            del self.attack[toDelete[i]]

    # print busters' commands
    def write_output(self):
        for v in self.busters:
            print(v.command)

    # main function
    def play_turn(self):
        # commands will be overwritten
        self.mark_visited_fields()
        self.del_fake_ghosts()
        self.update_last_seen_enemy()

        # scouting area for ghosts
        for i in range(0, len(self.busters)):
            self.busters[i].scout()

        self.delete_ejected()

        self.choose_targeted_ghost()
        self.bust_ghost()

        self.attack_enemy()

        # catching ejected ghost
        self.catch_ghost()

        self.save_ghost()

        self.stuning_system()

        self.throw_ghost()

        # use radar in the beginning of the game
        self.radar()

        # printing commands
        self.write_output()
        self.next_round()


# ***********************************************************************************************

game = gameLogic()
# game loop
while True:
    entities = int(input())  # the number of busters and ghosts visible to you

    currentBuster = 0
    for i in range(entities):
        # entity_id: buster id or ghost id
        # y: position of this buster / ghost
        # entity_type: the team id if it is a buster, -1 if it is a ghost.
        # state: For busters: 0=idle, 1=carrying a ghost.
        # value: For busters: Ghost id being carried. For ghosts: number of busters attempting to trap this ghost.
        entity_id, x, y, entity_type, state, value = [int(j) for j in input().split()]
        if (entity_type == my_team_id):
            # my busters
            game.busters[currentBuster].init_turn(x, y, entity_id, state, value)
            currentBuster += 1
        elif (entity_type == -1):
            # ghost
            j = 0
            while (j < len(game.ghosts) and game.ghosts[j].id != entity_id):
                j += 1
            if (j == len(game.ghosts)):
                # new ghost
                game.ghosts.append(ghost())
                game.ghosts[-1].init_turn(x, y, entity_id, state, value)
                game.ghosts[-1].visible = True
            else:
                # ghost already in list
                game.ghosts[j].init_turn(x, y, entity_id, state, value)
                game.ghosts[j].visible = True
        else:
            # enemy
            game.enemy.append(Entity())
            game.enemy[-1].init_turn(x, y, entity_id, state, value)
    game.play_turn()