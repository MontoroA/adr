
####################              Laboratorio 2025                            ####################
#################### Análisis y diseño de algoritmos distribuidos en redes    ####################
####################          Andrés Montoro 5.169.779-1                      ####################

from abc import ABC, abstractmethod
from math import floor
from pydistsim.algorithm.node_wrapper import NodeAccess
from pydistsim.message import Message
from pydistsim.network import Node
import random
from enum import Enum

# Estuve trabajando con la entrega hasta ultima hora, por lo que hay varios detalles que con mas tiempo se hubieran pulido
# Sobre todo en la herencia de Behavior. parametros en ordenes distintos entre las subclases, nombres distintos que implican kwarg, etc

def error(method : str, message: Message):
    msj = 'Unexpected message in ' + method + ' ' + message.header + " from " + str(message.source) + " , content: " + str(message.data)
    raise Exception(msj)

def raiseError(message: str):
    raise Exception(message)


class Siege():
    class State(Enum):
        ONGOING = "ongoing"
        SUCCESSFUL = "successful"
        FAILED = "failed"
        ABORTED = "aborted"

        def __str__(self):
            return self.value

    def __init__(self, n, log, success_threshold = None, success_rate = 0.5):
        self.siegers = n
        self.attackers = 0
        self.retreaters = 0
        self.crashers = 0
        self.state = self.State.ONGOING
        self.success_threshold = success_threshold if success_threshold else n
        self.success_rate = success_rate
        self.log = log

    def observe(self, node: NodeAccess):
        d = random.random()
        should_retreat = d < (1 - self.success_rate)
        if should_retreat:
            return GeneralDecision.RETREAT
        return GeneralDecision.ATTACK

    def attack_in_place(self):
        if self.attackers >= self.success_threshold:
            self.log("[Siege] All loyal generals attacked. Successful siege")
            self.state = self.State.SUCCESSFUL
        elif self.attackers == 0:
            self.log("[Siege] All loyal generals retreat from siege")
            self.state = self.State.ABORTED
        else:
            self.log("[Siege] Only some generals attacked. Failed siege")
            self.state = self.State.FAILED

    def attack(self, node: NodeAccess):
        self.log(f"[{node.memory['unique_value']}] Attacking")
        self.attackers += 1
        if self.attackers + self.retreaters + self.crashers == self.siegers:
            self.attack_in_place()

    def retreat(self, node: NodeAccess):
        self.log(f"[General {node.memory['unique_value']}] Retreating")
        self.retreaters += 1
        if self.attackers + self.retreaters + self.crashers == self.siegers:
            self.attack_in_place()

    def crash(self, node: NodeAccess):
        self.log(f"[General {node.memory['unique_value']}] Crashed")
        self.crashers += 1
        if self.attackers + self.retreaters + self.crashers == self.siegers:
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

class EncryptedData():
    def __init__(self, value):
        self.value = value


def send_and_count(
        node : NodeAccess, 
        datos : Data, 
        dest : list | Node, 
        msj_type : str, 
        algorithm,
        msj_counter = True
    ):
    algorithm.send(
        node, 
        data=datos,
        destination=dest,
        header=msj_type
    )
    if msj_counter:
        algorithm.messages_counter += 1



class Behavior(ABC):
    @abstractmethod
    def send(*args, **kwargs):
        pass



class NonFaultyBehavior(Behavior):
    def __init__(self):
        pass

    def send(
            self, 
            node : NodeAccess, 
            algorithm, 
            header, 
            destination
        ):
        private_key = node.memory["private_key"]
        firma = b"My signature"
        signature = private_key.sign(firma)
        msj = EncryptedData(signature)
        send_and_count(
            node,
            datos = msj,
            dest = destination,
            msj_type = header,
            algorithm = algorithm,
            msj_counter = False
        )



class ByzantineBehavior(Behavior):
    class Behavior(Enum):
        LIER = "lier"
        QUIET = "quiet"
        CONFUSER = "confuser"

    def __init__(self, behavior : Behavior):
        self.behavior = behavior

    def send(
        self, 
        node : NodeAccess, 
        algorithm, 
        header, 
        destination : set, 
        path : str = None, 
        rcvd_decision : GeneralDecision = None
        ):
        if self.behavior == ByzantineBehavior.Behavior.LIER:
            self.lie(
                node, 
                algorithm, 
                destination, 
                header, 
                path, 
                rcvd_decision
            )
        elif self.behavior == ByzantineBehavior.Behavior.QUIET:
            self.quiet()
        elif self.behavior == ByzantineBehavior.Behavior.CONFUSER:
            self.confuse(
                node, 
                algorithm, 
                header, 
                destination, 
                path
            )

    def confuse(
            self, 
            node : NodeAccess, 
            algorithm, 
            header, 
            destination : set,
            path : str = None
        ):
        half = int(len(destination)/2)
        attackers = random.sample(list(destination), half)
        retreaters = [x for x in destination if x not in attackers]     
        
        datosAttackers = Data(
            path = path,
            value = GeneralDecision.ATTACK
        )
        datosRetreaters = Data(
            path = path,
            value = GeneralDecision.RETREAT
        )
        send_and_count(
            node=node, 
            datos=datosAttackers,
            dest=attackers,
            msj_type=header,
            algorithm=algorithm
        )
        send_and_count(
            node=node, 
            datos=datosRetreaters,
            dest=retreaters,
            msj_type=header,
            algorithm=algorithm
        )

    def lie(
            self, 
            general : NodeAccess, 
            algorithm, 
            destination : set, 
            header, 
            path : str = None, 
            rcvd_decision : GeneralDecision = None
        ):
        if rcvd_decision is GeneralDecision.RETREAT:
            lie = GeneralDecision.ATTACK
        elif rcvd_decision is GeneralDecision.ATTACK:
            lie = GeneralDecision.RETREAT
        else:
            lie = GeneralDecision.ATTACK
        bromita = Data(
            path = path,
            value = lie
        )
        send_and_count(
            general, 
            datos=bromita,
            dest=destination,
            msj_type=header,
            algorithm=algorithm
        )
        
    def quiet():
        pass

class CrashBehavior(Behavior):
    def __init__(self, node : NodeAccess, log):
        self.crash_chance = self.crash_chance()
        self.log = log

    def send(
            self, 
            node : NodeAccess, 
            algorithm, 
            header, 
            destination, 
            chance = False, 
        ):
        if not isinstance(destination, set):
            destination = {destination}
        for neighbor in destination:
            if(chance and self.determine_crash(node)):
                return False
            self.log(f"[Node {node.memory['unique_value']}] Sending '{header}' to node {neighbor}")
            algorithm.send(
                node, 
                data=None,
                destination=neighbor,
                header=header
            )
        return True

    def crash_chance(node: NodeAccess):
        # TODO fallos configurables
        # return random.random()
        return 0.1

    def determine_crash(self, node: NodeAccess):
        d = random.random()
        if d < self.crash_chance:
            return True
        return False
