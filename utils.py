
from math import floor
from pydistsim.algorithm.node_wrapper import NodeAccess
from pydistsim.message import Message
from pydistsim.network import Node
from pydistsim.logging import set_log_level, LogLevels, enable_logger, logger
import random
from enum import Enum

set_log_level(LogLevels.INFO)
enable_logger()



def error(method : str, message: Message):
    msj = 'Unexpected message in ' + method + message.header + " from " + str(message.source) + " , content: " + str(message.data)
    raise Exception(msj)



#TODO Success only if all loyal liutenants attack
class Siege():
    def __init__(self, n, attack_success_threshold = None):
        self.siegers = n
        self.attackers = 0
        self.retreaters = 0
        self.attack_success_threshold = attack_success_threshold if attack_success_threshold else n/2

    def attack_in_place(self):
        if self.attackers >= self.attack_success_threshold:
            logger.info("[{}] All loyal generals attacked. Successful siege", "Siege")
        elif self.attackers == 0:
            logger.info("[{}] All loyal generals retreat from siege", "Siege")
        else:
            logger.info("[{}] Only some generals attacked. Failed siege", "Siege")

    def attack(self, node : NodeAccess):
        logger.info("[{}] Attacking", f"General {node.memory['unique_value']}")
        self.siegers -= 1
        self.attackers += 1
        if self.siegers == 0:
            self.attack_in_place()

    def retreat(self, node : NodeAccess):
        logger.info("[{}] Retreating", f"General {node.memory['unique_value']}")
        self.siegers -= 1
        self.retreaters += 1
        if self.siegers == 0:
            self.attack_in_place()



class GeneralDecision(Enum):
    RETREAT = "retreat" 
    ATTACK  = "attack"
    
    @staticmethod
    def lie(decision):
        if decision is GeneralDecision.RETREAT:
            return GeneralDecision.ATTACK
        if decision is GeneralDecision.ATTACK:
            return GeneralDecision.RETREAT
        return None

    def __str__(self):
        return self.value


def define_general_threshold(_ : Node):
    # Eventualmente puede establecerse un threshold especifico de acuerdo a las condiciones del nodo
    return 0.5



def observe(node: NodeAccess):
    d = random.random()
    should_retreat = d < node.memory["observed_success_chance"]
    logger.info(
        "[{}] Observes they should {}" , 
        f"General {node.memory['unique_value']}", 
        "retreat" if should_retreat else "attack"
    )
    if should_retreat:
        return GeneralDecision.RETREAT
    return GeneralDecision.ATTACK



def majority(decisions: dict):
    # 1. The majority value among the vi if it exists, otherwise the value RETREAT;
    print(decisions)
    values = decisions.values()  #if v is not None else GeneralDecision.RETREAT
    attackers = len([1 for v in values if v == GeneralDecision.ATTACK])
    if attackers > floor(len(values)/2):
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
    #FIXME implementar control. Corresponde que este en una interfaz al send?
    # if msj_type == algorithm.default_params["Value"]:
    #     unique_value_sent = datos.path[-1]
    #     if node.memory["unique_value"] != unique_value_sent:
    #         # 3.A2
    #         raise ValueError(f"General {node.memory['unique_value']} tried to send inconsistent observation: {unique_value_sent}")
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
        half = int(len(general.neighbors())/2)
        attackers = random.sample(list(general.neighbors()), half)
        retreaters = [x for x in general.neighbors() if x not in attackers]     
        
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