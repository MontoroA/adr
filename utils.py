
from math import floor
from pydistsim.algorithm.node_wrapper import NodeAccess
from pydistsim.message import Message
from pydistsim.network import Node
from pydistsim.logging import logger
import random
from enum import Enum


def error(method : str, message: Message):
    msj = 'Unexpected message in ' + method + ' ' + message.header + " from " + str(message.source) + " , content: " + str(message.data)
    raise Exception(msj)

def error(message: str):
    raise Exception(message)


######################################################################################################################################################
#################################################        ORAL MESSAGES  UTILS             ############################################################
######################################################################################################################################################

class Siege():
    class State(Enum):
        ONGOING = "ongoing"
        SUCCESSFUL = "successful"
        FAILED = "failed"
        ABORTED = "aborted"

    def __init__(self, n, success_threshold = None, success_rate = 0.5):
        self.siegers = n
        self.attackers = 0
        self.retreaters = 0
        self.state = self.State.ONGOING
        self.success_threshold = success_threshold if success_threshold else n
        self.success_rate = success_rate

    def observe(self, node: NodeAccess):
        d = random.random()
        should_retreat = d < (1 - self.success_rate)
        if should_retreat:
            return GeneralDecision.RETREAT
        return GeneralDecision.ATTACK

    def attack_in_place(self):
        if self.attackers >= self.success_threshold:
            logger.info("[{}] All loyal generals attacked. Successful siege", "Siege")
            self.state = self.State.SUCCESSFUL
        elif self.attackers == 0:
            logger.info("[{}] All loyal generals retreat from siege", "Siege")
            self.state = self.State.ABORTED
        else:
            logger.info("[{}] Only some generals attacked. Failed siege", "Siege")
            self.state = self.State.FAILED

    def attack(self):
        self.siegers -= 1
        self.attackers += 1
        if self.siegers == 0:
            self.attack_in_place()

    def retreat(self):
        self.siegers -= 1
        self.retreaters += 1
        if self.siegers == 0:
            self.attack_in_place()



class GeneralDecision(Enum):
    RETREAT = "retreat" 
    ATTACK  = "attack"
    
    def __str__(self):
        return self.value


def majority(decisions: dict):
    # 1. The majority value among the vi if it exists, otherwise the value RETREAT;
    attackers = len([1 for v in decisions if v == GeneralDecision.ATTACK])
    retreaters = len(decisions) - attackers
    if attackers > retreaters:
        return GeneralDecision.ATTACK
    return GeneralDecision.RETREAT



class Data:
    def __init__(self, path : tuple, value : GeneralDecision):
        self.path = path
        self.value = value

    def __str__(self):
        return f"Data: {self.path}, {self.value}"



def send_with_check(
        node : NodeAccess, 
        datos : Data, 
        dest : list | Node, 
        msj_type : str, 
        algorithm,
    ):
    #FIXME implementar control 3.A2. Corresponde que este en una interfaz al send?
    # if msj_type == algorithm.default_params["Value"]:
    #     if node.memory["unique_value"] != datos.path[-1]:
    #         raise ValueError(f"General {node.memory['unique_value']} tried to send inconsistent observation: {datos.path[-1]}")
    algorithm.send(
        node, 
        data=datos,
        destination=dest,
        header=msj_type
    )
    algorithm.messages_counter += 1



class TraitorActions:
    @staticmethod
    def send_confusing_signal(general : NodeAccess, algorithm, datos : Data = None, sender = None):
        half = int(len(general.memory["liutenants"])/2)
        attackers = random.sample(list(general.memory["liutenants"]), half)
        retreaters = [x for x in general.memory["liutenants"] if x not in attackers]     
        
        datosAttackers = Data(
            path = datos.path,
            value = GeneralDecision.ATTACK
        )
        datosRetreaters = Data(
            path = datos.path,
            value = GeneralDecision.RETREAT
        )

        if sender:
            attackers = set(attackers) - {sender}
            retreaters = set(retreaters) - {sender}

        send_with_check(
            general, 
            datos=datosAttackers,
            dest=attackers,
            msj_type=algorithm.default_params["Value"],
            algorithm=algorithm
        )
        send_with_check(
            general, 
            datos=datosRetreaters,
            dest=retreaters,
            msj_type=algorithm.default_params["Value"],
            algorithm=algorithm
        )

    @staticmethod
    def lie(decision):
        if decision is GeneralDecision.RETREAT:
            return GeneralDecision.ATTACK
        if decision is GeneralDecision.ATTACK:
            return GeneralDecision.RETREAT
        return None
    



######################################################################################################################################################
#################################################               2PC  UTILS                ############################################################
######################################################################################################################################################

class CrashBehavior():
    @staticmethod
    def crash_chance(node: NodeAccess):
        # TODO fallos configurables
        # return random.random()
        return 0.1

    @staticmethod
    def determine_crash(node: NodeAccess):
        d = random.random()
        if d < node.memory["crash_chance"]:
            return True
        return False

class Transaction():
    class TransactionState(Enum):
        ONGOING = "ongoing"
        COMMITTED = "committed"
        ABORTED = "aborted"
        INCONSISTENT = "inconsistent"
        DEADLOCK = "deadlock"

    def __init__(self, n):
        self.participants = n
        self.committers = 0
        self.aborters = 0
        self.state = self.TransactionState.ONGOING

    def result(self):
        if self.committers == self.participants:
            logger.info("[Transaction] All nodes committed the transaction. Consistency achieved")
            self.state = self.TransactionState.COMMITTED
        elif self.aborters == self.participants:
            logger.info("[Transaction] All nodes aborted the transaction. Consistency preserved")
            self.state = self.TransactionState.ABORTED
        else:
            logger.info("[Transaction] Only some nodes commited the transaction. Inconsistency occurred")
            self.state = self.TransactionState.INCONSISTENT

    def commit(self):
        if self.state != self.TransactionState.ONGOING:
            return
        self.committers += 1
        if self.committers + self.aborters == self.participants:
            self.result()

    def abort(self):
        if self.state != self.TransactionState.ONGOING:
            return
        self.aborters += 1
        if self.committers + self.aborters == self.participants:
            self.result()

    def crash(self):
        self.participants -= 1

    def declare_deadlock(self):
        logger.info("[Transaction] Deadlock ocurred")
        self.state = self.TransactionState.DEADLOCK