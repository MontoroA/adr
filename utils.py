
from pydistsim.algorithm.node_wrapper import NodeAccess
from pydistsim.network import Node
from pydistsim.logging import set_log_level, LogLevels, enable_logger, logger

set_log_level(LogLevels.INFO)
enable_logger()


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

def define_general_threshold(general : Node):
    # Eventualmente puede establecerse un threshold especifico de acuerdo a las condiciones del nodo
    return 0.5


class TraitorActions:
    @staticmethod
    def random_behaviour():
        pass

    @staticmethod
    def init(node : NodeAccess, algorithm):
        logger.info("[{}] Is a traitor, so he sends the opposite decision", f"General {node.memory['unique_value']}")
        lie = GeneralDecision.lie(node.memory["decisions"][node.memory["unique_value"]])
        algorithm.send(
            node, 
            data=(lie, node.memory["unique_value"]),
            destination=node.memory["commander"],
            header=algorithm.default_params["Observation"]
        )

    @staticmethod
    def commander_decision(node : NodeAccess, algorithm):
        siege : Siege = node.memory["siege"]
        half = int(len(node.neighbors())/2)
        attackers = random.sample(list(node.neighbors()), half)
        retreaters = [x for x in node.neighbors() if x not in attackers]
        algorithm.send(
            node, 
            data=GeneralDecision.ATTACK,
            destination=attackers,
            header=algorithm.default_params["Decision"]
        )
        algorithm.send(
            node, 
            data=GeneralDecision.RETREAT,
            destination=retreaters,
            header=algorithm.default_params["Decision"]
        )
        # Asumo que los traidores no atacan
        siege.retreat(node)
        node.status = algorithm.Status.RETREAT
    
    @staticmethod
    def respond_order(node : NodeAccess, algorithm):
        # Asumo que los traidores no atacan
        siege : Siege = node.memory["siege"]
        siege.retreat(node)
        node.status = algorithm.Status.RETREAT