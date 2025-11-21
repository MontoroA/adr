
from math import floor
from pydistsim.algorithm.node_wrapper import NodeAccess
from pydistsim.message import Message
from pydistsim.network import Node
from pydistsim.logging import set_log_level, LogLevels, enable_logger, logger
import random


set_log_level(LogLevels.INFO)
enable_logger()


def error(method : str, message: Message):
    msj = 'Unexpected message in ' + method + message.header + " from " + str(message.source) + " , content: " + str(message.data)
    raise Exception(msj)


def observe(node: NodeAccess):
    d = random.random()
    should_retreat = d < node.memory["decision_threshold"]
    logger.info(
        "[{}] Observes they should {}" , 
        f"General {node.memory['unique_value']}", 
        "retreat" if should_retreat else "attack"
    )
    if should_retreat:
        return GeneralDecision.RETREAT
    return GeneralDecision.ATTACK


def decide(node: NodeAccess):
    if len([1 for (id, decision) in node.memory["decisions"].items() if decision == GeneralDecision.ATTACK]) >= int((len(node.neighbors()) + 1)/2):
        return GeneralDecision.ATTACK
    return GeneralDecision.RETREAT
 


def majority(values: dict):
    # 1. The majority value among the vi if it exists, otherwise the value RETREAT;
    vi = [v for v in values.values() if v is not None]
    attackers = len([1 for v in vi if v == GeneralDecision.ATTACK])
    if attackers > floor(len(vi)/2):
        return GeneralDecision.ATTACK
    return GeneralDecision.RETREAT

def define_general_threshold(general : Node):
    # Eventualmente puede establecerse un threshold especifico de acuerdo a las condiciones del nodo
    return 0.5

def send_with_check(node : NodeAccess, datos : any, dest : list | Node, msj_type : str, algorithm):
    if msj_type == algorithm.default_params["Observation"]:
        unique_value_sent = datos[1]
        if node.memory["unique_value"] != unique_value_sent:
            # 3.A2
            raise ValueError(f"General {node.memory['unique_value']} tried to send inconsistent observation: {unique_value_sent}")
    algorithm.send(
        node, 
        data=datos,
        destination=dest,
        header=msj_type
    )
    if algorithm.messages_counter:
        algorithm.messages_counter += 1


class Siege():
    def __init__(self, n, attack_success_threshold = None):
        self.siegers = n
        self.attackers = 0
        self.retreaters = 0
        self.attack_success_threshold =  attack_success_threshold if attack_success_threshold else n/2

    def attack_in_place(self):
        if self.attackers >= self.attack_success_threshold:
            logger.info("[{}] Successfull siege", "Siege")
        elif self.attackers == 0:
            logger.info("[{}] Army retreats from siege", "Siege")
        else:
            logger.info("[{}] Failed attack", "Siege")

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


class GeneralDecision:
    RETREAT = "retreat" 
    ATTACK  = "attack"
    
    @staticmethod
    def lie(decision):
        if not decision:
            return None
        if decision == GeneralDecision.RETREAT:
            return GeneralDecision.ATTACK
        if decision == GeneralDecision.ATTACK:
            return GeneralDecision.RETREAT

class TraitorActions:
    @staticmethod
    def random_behaviour():
        pass

    @staticmethod
    def init(node : NodeAccess, algorithm):
        logger.info("[{}] Is a traitor, so he sends the opposite decision", f"General {node.memory['unique_value']}")
        if node.status == algorithm.Status.LIUTENANT:
            lie = GeneralDecision.lie(node.memory["decisions"][node.memory["unique_value"]])
            send_with_check(
                node,
                datos=(lie, node.memory["unique_value"]),
                dest=node.memory["commander"],
                msj_type=algorithm.default_params["Observation"],
                algorithm=algorithm
            )

    @staticmethod
    def commander_decision(node : NodeAccess, algorithm):
        siege : Siege = algorithm.siege
        half = int(len(node.neighbors())/2)
        attackers = random.sample(list(node.neighbors()), half)
        retreaters = [x for x in node.neighbors() if x not in attackers]
        
        send_with_check(
            node, 
            datos=GeneralDecision.ATTACK,
            dest=attackers,
            msj_type=algorithm.default_params["Decision"],
            algorithm=algorithm
        )
        send_with_check(
            node, 
            datos=GeneralDecision.RETREAT,
            dest=retreaters,
            msj_type=algorithm.default_params["Decision"],
            algorithm=algorithm
        )
        # Asumo que los traidores no atacan
        siege.retreat(node)
        node.status = algorithm.Status.RETREAT
    
    @staticmethod
    def respond_order(node : NodeAccess, algorithm):
        # Asumo que los traidores no atacan
        siege : Siege = algorithm.siege
        siege.retreat(node)
        node.status = algorithm.Status.RETREAT