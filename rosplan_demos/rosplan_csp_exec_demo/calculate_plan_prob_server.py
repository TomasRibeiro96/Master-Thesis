#!/usr/bin/env python

import sys
import rospy
from rosplan_knowledge_msgs.srv import *
from rosplan_knowledge_msgs.msg import *
from rosplan_dispatch_msgs.msg import EsterelPlanArray
from rosplan_dispatch_msgs.msg import EsterelPlan
from rosplan_dispatch_msgs.srv import CalculateProbability, CalculateProbabilityResponse
from std_msgs.msg import String
import matplotlib
import matplotlib.pyplot as plt
from numpy import *
from pomegranate import *
import collections
import time

pred_probabilities_map = dict()
action_probabilities_map = dict()
cpds_map = dict()
receivedPlan = False
testing = False
returned_times = 1

#### TODO: Retornar os predicados relevantes em cada layer para verificar se eh preciso replanear depois de executar acao

class Action:

    actionsList = list()

    def __init__(self, name, duration = 0):
        if not isinstance(name, str):
            raise TypeError("Action name not a String")
        self.name = name
        self.duration = duration

        self.parameters = list()
        operator_details = rospy.ServiceProxy('/rosplan_knowledge_base/domain/operator_details', GetDomainOperatorDetailsService)(name)
        rospy.ServiceProxy('/rosplan_knowledge_base/domain/operator_details', GetDomainOperatorDetailsService)
        number_param = len(operator_details.op.formula.typed_parameters)
        for i in range(number_param):
            self.parameters.append(operator_details.op.formula.typed_parameters[i].key)

        ### Getting effects and conditions from operator_details ###
        # I couldn't use a cycle because the parameter name of operator_details changes
        self.effects = dict()
        self.conditions = dict()
        self.comparison = dict()

        # at_start_add_effects
        self.effects['at_start_add_effects'] = list()
        if operator_details.op.at_start_add_effects:
            number_pred = len(operator_details.op.at_start_add_effects)
            for i in range(number_pred):
                self.effects['at_start_add_effects'].append(list())
                predicate_name = operator_details.op.at_start_add_effects[i].name
                self.effects['at_start_add_effects'][i].append(predicate_name)
                number_param = len(operator_details.op.at_start_add_effects[i].typed_parameters)
                for j in range(number_param):
                    variable = operator_details.op.at_start_add_effects[i].typed_parameters[j].key
                    self.effects['at_start_add_effects'][i].append(variable)
        
        # at_start_del_effects
        self.effects['at_start_del_effects'] = list()
        if operator_details.op.at_start_del_effects:
            number_pred = len(operator_details.op.at_start_del_effects)
            for i in range(number_pred):
                self.effects['at_start_del_effects'].append(list())
                predicate_name = operator_details.op.at_start_del_effects[i].name
                self.effects['at_start_del_effects'][i].append(predicate_name)
                number_param = len(operator_details.op.at_start_del_effects[i].typed_parameters)
                for j in range(number_param):
                    variable = operator_details.op.at_start_del_effects[i].typed_parameters[j].key
                    self.effects['at_start_del_effects'][i].append(variable)

        # at_end_add_effects
        self.effects['at_end_add_effects'] = list()
        if operator_details.op.at_end_add_effects:
            number_pred = len(operator_details.op.at_end_add_effects)
            for i in range(number_pred):
                self.effects['at_end_add_effects'].append(list())
                predicate_name = operator_details.op.at_end_add_effects[i].name
                self.effects['at_end_add_effects'][i].append(predicate_name)
                number_param = len(operator_details.op.at_end_add_effects[i].typed_parameters)
                for j in range(number_param):
                    variable = operator_details.op.at_end_add_effects[i].typed_parameters[j].key
                    self.effects['at_end_add_effects'][i].append(variable)

        # at_end_del_effects
        self.effects['at_end_del_effects'] = list()
        if operator_details.op.at_end_del_effects:
            number_pred = len(operator_details.op.at_end_del_effects)
            for i in range(number_pred):
                self.effects['at_end_del_effects'].append(list())
                predicate_name = operator_details.op.at_end_del_effects[i].name
                self.effects['at_end_del_effects'][i].append(predicate_name)
                number_param = len(operator_details.op.at_end_del_effects[i].typed_parameters)
                for j in range(number_param):
                    variable = operator_details.op.at_end_del_effects[i].typed_parameters[j].key
                    self.effects['at_end_del_effects'][i].append(variable)

        # at_start_assign_effects
        self.effects['at_start_assign_effects'] = list()
        if operator_details.op.at_start_assign_effects:
            number_pred = len(operator_details.op.at_start_assign_effects)
            for i in range(number_pred):
                self.effects['at_start_assign_effects'].append(list())
                predicate_name = operator_details.op.at_start_assign_effects[i].name
                self.effects['at_start_assign_effects'][i].append(predicate_name)
                number_param = len(operator_details.op.at_start_assign_effects[i].typed_parameters)
                for j in range(number_param):
                    variable = operator_details.op.at_start_assign_effects[i].typed_parameters[j].key
                    self.effects['at_start_assign_effects'][i].append(variable)

        # at_end_assign_effects
        self.effects['at_end_assign_effects'] = list()
        if operator_details.op.at_end_assign_effects:
            number_pred = len(operator_details.op.at_end_assign_effects)
            for i in range(number_pred):
                self.effects['at_end_assign_effects'][i].append(list())
                predicate_name = operator_details.op.at_end_assign_effects[i].name
                self.effects['at_end_assign_effects'][i].append(predicate_name)
                number_param = len(operator_details.op.at_end_assign_effects[i].typed_parameters)
                for j in range(number_param):
                    variable = operator_details.op.at_end_assign_effects[i].typed_parameters[j].key
                    self.effects['at_end_assign_effects'][i].append(variable)

        # probabilistic_effects
        self.effects['probabilistic_effects'] = list()
        if operator_details.op.probabilistic_effects:
            self.effects['probabilistic_effects'].append[list()]
            number_pred = len(operator_details.op.probabilistic_effects)
            for i in range(number_pred):
                predicate_name = operator_details.op.probabilistic_effects[i].name
                self.effects['probabilistic_effects'][i].append(predicate_name)
                number_param = len(operator_details.op.probabilistic_effects[i].typed_parameters)
                for j in range(number_param):
                    variable = operator_details.op.probabilistic_effects[i].typed_parameters[j].key
                    self.effects['probabilistic_effects'][i].append(variable)

        # at_start_simple_condition
        self.conditions['at_start_simple_condition'] = list()
        if operator_details.op.at_start_simple_condition:
            number_pred = len(operator_details.op.at_start_simple_condition)
            for i in range(number_pred):
                self.conditions['at_start_simple_condition'].append(list())
                predicate_name = operator_details.op.at_start_simple_condition[i].name
                self.conditions['at_start_simple_condition'][i].append(predicate_name)
                number_param = len(operator_details.op.at_start_simple_condition[i].typed_parameters)
                for j in range(number_param):
                    variable = operator_details.op.at_start_simple_condition[i].typed_parameters[j].key
                    self.conditions['at_start_simple_condition'][i].append(variable)

        # over_all_simple_condition
        self.conditions['over_all_simple_condition'] = list()
        if operator_details.op.over_all_simple_condition:
            number_pred = len(operator_details.op.over_all_simple_condition)
            for i in range(number_pred):
                self.conditions['over_all_simple_condition'].append(list())
                predicate_name = operator_details.op.over_all_simple_condition[i].name
                self.conditions['over_all_simple_condition'][i].append(predicate_name)
                number_param = len(operator_details.op.over_all_simple_condition[i].typed_parameters)
                for j in range(number_param):
                    variable = operator_details.op.over_all_simple_condition[i].typed_parameters[j].key
                    self.conditions['over_all_simple_condition'][i].append(variable)

        # at_end_simple_condition
        self.conditions['at_end_simple_condition'] = list()
        if operator_details.op.at_end_simple_condition:
            number_pred = len(operator_details.op.at_end_simple_condition)
            for i in range(number_pred):
                self.conditions['at_end_simple_condition'].append(list())
                predicate_name = operator_details.op.at_end_simple_condition[i].name
                self.conditions['at_end_simple_condition'][i].append(predicate_name)
                number_param = len(operator_details.op.at_end_simple_condition[i].typed_parameters)
                for j in range(number_param):
                    variable = operator_details.op.at_end_simple_condition[i].typed_parameters[j].key
                    self.conditions['at_end_simple_condition'][i].append(variable)

        # at_start_neg_condition
        self.conditions['at_start_neg_condition'] = list()
        if operator_details.op.at_start_neg_condition:
            number_pred = len(operator_details.op.at_start_neg_condition)
            for i in range(number_pred):
                self.conditions['at_start_neg_condition'].append(list())
                predicate_name = operator_details.op.at_start_neg_condition[i].name
                self.conditions['at_start_neg_condition'][i].append(predicate_name)
                number_param = len(operator_details.op.at_start_neg_condition[i].typed_parameters)
                for j in range(number_param):
                    variable = operator_details.op.at_start_neg_condition[i].typed_parameters[j].key
                    self.conditions['at_start_neg_condition'][i].append(variable)

        # over_all_neg_condition
        self.conditions['over_all_neg_condition'] = list()
        if operator_details.op.over_all_neg_condition:
            number_pred = len(operator_details.op.over_all_neg_condition)
            for i in range(number_pred):
                self.conditions['over_all_neg_condition'].append(list())
                predicate_name = operator_details.op.over_all_neg_condition[i].name
                self.conditions['over_all_neg_condition'][i].append(predicate_name)
                number_param = len(operator_details.op.over_all_neg_condition[i].typed_parameters)
                for j in range(number_param):
                    variable = operator_details.op.over_all_neg_condition[i].typed_parameters[j].key
                    self.conditions['over_all_neg_condition'][i].append(variable)

        # at_end_neg_condition
        self.conditions['at_end_neg_condition'] = list()
        if operator_details.op.at_end_neg_condition:
            number_pred = len(operator_details.op.at_end_neg_condition)
            for i in range(number_pred):
                self.conditions['at_end_neg_condition'].append(list())
                predicate_name = operator_details.op.at_end_neg_condition[i].name
                self.conditions['at_end_neg_condition'][i].append(predicate_name)
                number_param = len(operator_details.op.at_end_neg_condition[i].typed_parameters)
                for j in range(number_param):
                    variable = operator_details.op.at_end_neg_condition[i].typed_parameters[j].key
                    self.conditions['at_end_neg_condition'][i].append(variable)

        # at_start_comparison
        self.comparison['at_start_comparison'] = list()
        if operator_details.op.at_start_comparison:
            number_pred = len(operator_details.op.at_start_comparison)
            for i in range(number_pred):
                self.comparison['at_start_comparison'].append(list())
                predicate_name = operator_details.op.at_start_comparison[i].name
                self.comparison['at_start_comparison'][i].append(predicate_name)
                number_param = len(operator_details.op.at_start_comparison[i].typed_parameters)
                for j in range(number_param):
                    variable = operator_details.op.at_start_comparison[i].typed_parameters[j].key
                    self.comparison['at_start_comparison'][i].append(variable)

        # at_end_comparison
        self.comparison['at_end_comparison'] = list()
        if operator_details.op.at_end_comparison:
            number_pred = len(operator_details.op.at_end_comparison)
            for i in range(number_pred):
                self.comparison['at_end_comparison'].append(list())
                predicate_name = operator_details.op.at_end_comparison[i].name
                self.comparison['at_end_comparison'][i].append(predicate_name)
                number_param = len(operator_details.op.at_end_comparison[i].typed_parameters)
                for j in range(number_param):
                    variable = operator_details.op.at_end_comparison[i].typed_parameters[j].key
                    self.comparison['at_end_comparison'][i].append(variable)

        # over_all_comparison
        self.comparison['over_all_comparison'] = list()
        if operator_details.op.over_all_comparison:
            number_pred = len(operator_details.op.over_all_comparison)
            for i in range(number_pred):
                self.comparison['over_all_comparison'].append(list())
                predicate_name = operator_details.op.over_all_comparison[i].name
                self.comparison['over_all_comparison'][i].append(predicate_name)
                number_param = len(operator_details.op.over_all_comparison[i].typed_parameters)
                for j in range(number_param):
                    variable = operator_details.op.over_all_comparison[i].typed_parameters[j].key
                    self.comparison['over_all_comparison'][i].append(variable)

        Action.actionsList.append(self)
    

    def printAction(self):
        print('>>>>>>>>>>>>>>>>>>>>>>>>')
        print('Action name: ' + self.name)
        print('Action duration: ' + str(self.duration))
        print('Conditions: ' + str(self.conditions))
        print('Effects: ' + str(self.effects))
        print('Comparison: ' + str(self.comparison))
        print('<<<<<<<<<<<<<<<<<<<<<<<<')

    @classmethod
    def getAction(cls, action_name):
        for item in Action.actionsList:
            if item.name == action_name:
                return item
        return None

    @classmethod
    def getActionNamesList(cls):
        names_list = list()
        for item in Action.actionsList:
            names_list.append(item.name)
        return names_list



class GroundedAction:

    actionsList = list()

    def __init__(self, action, list_objects):
        # Action duration is missing
        variables = action.parameters
        var_obj = dict(zip(variables, list_objects))
        self.name = str( action.name + '#' + '#'.join(str(v) for v in list_objects))

        self.effects = dict()
        for k, v in action.effects.items():
            self.effects[k] = list()
            if v:
                i = 0
                for value in v:
                    self.effects[k].append(list())
                    for item in value:
                        if item in list(var_obj.keys()):
                            self.effects[k][i].append(var_obj[item])
                        else:
                            self.effects[k][i].append(item)
                    i = i + 1
            else:
                self.effects[k] = v
        
        self.conditions = dict()
        for k, v in action.conditions.items():
            self.conditions[k] = list()
            if v:
                i = 0
                for value in v:
                    self.conditions[k].append(list())
                    for item in value:
                        if item in list(var_obj.keys()):
                            self.conditions[k][i].append(var_obj[item])
                        else:
                            self.conditions[k][i].append(item)
                    i = i + 1
            else:
                self.conditions[k] = v

        self.comparison = dict()
        for k, v in action.comparison.items():
            self.comparison[k] = list()
            if v:
                for value in v:
                    self.comparison[k].append(list())
                    for item in value:
                        if item in list(var_obj.keys()):
                            self.comparison[k][i].append(var_obj[item])
                        else:
                            self.comparison[k][i].append(item)
                    i = i + 1
            else:
                self.comparison[k] = v
        
        GroundedAction.actionsList.append(self)


    def getPredicates(self):
        predicates_set = set()
        for k, v in self.conditions.items():
            for predicate in v:
                predicates_set.add('#'.join(predicate))
        for k, v in self.effects.items():
            for predicate in v:
                predicates_set.add('#'.join(predicate))
        for k, v in self.comparison.items():
            for predicate in v:
                predicates_set.add('#'.join(predicate))
        
        return predicates_set


    @classmethod
    def getAllPredicates(cls):
        predicates_set = set()
        for action in GroundedAction.actionsList:
            for predicate in action.getPredicates():
                predicates_set.add(predicate)

        return predicates_set


    def printAction(self):
        print('>>>>>>>>>>>>>>>>>>>>>>>>')
        print('Grounded Action name: ' + self.name)
        # print('Action duration: ' + str(self.duration))
        print('Conditions: ' + str(self.conditions))
        print('Effects: ' + str(self.effects))
        print('Comparison: ' + str(self.comparison))
        print('<<<<<<<<<<<<<<<<<<<<<<<<')


    @classmethod
    def getGroundedAction(cls, action_name):
        for item in GroundedAction.actionsList:
            if item.name == action_name:
                return item
        return None


    @classmethod
    def getGroundedActionsList(cls):
        list_actions = list()
        for grounded_action in GroundedAction.actionsList:
            list_actions.append(grounded_action.name)
        return list_actions



class ActionStart:

    actionsList = list()

    def __init__(self, grounded_action):
        name_act = grounded_action.name.split('#')
        name_act[0] = name_act[0] + '_start'
        self.name = '#'.join(name_act)
        # Name format: goto_waypoint#robot0#wp0#machine

        self.conditions = dict()
        for k, v in grounded_action.conditions.items():
            if k[:8] == 'at_start':
                self.conditions[k[9:]] = grounded_action.conditions[k]
        
        self.effects = dict()
        for k, v in grounded_action.effects.items():
            if k[:8] == 'at_start':
                self.effects[k[9:]] = grounded_action.effects[k]
        
        ActionStart.actionsList.append(self)


    def getPredicates(self):
        predicates_set = set()
        for k, v in self.conditions.items():
            for predicate in v:
                predicates_set.add('#'.join(predicate))
        for k, v in self.effects.items():
            for predicate in v:
                predicates_set.add('#'.join(predicate))
        for k, v in self.comparison.items():
            for predicate in v:
                predicates_set.add('#'.join(predicate))
        
        return predicates_set


    def getConditionPredicates(self):
        predicates_set = set()
        for k, v in self.conditions.items():
            for predicate in v:
                predicates_set.add('#'.join(predicate))
        
        return predicates_set


    def getEffectsPredicates(self):
        predicates_set = set()
        for k, v in self.effects.items():
            for predicate in v:
                predicates_set.add('#'.join(predicate))
        
        return predicates_set


    def printAction(self):
        print('>>>>>>>>>>>>>>>>>>>>>>>>')
        print('ActionStart name: ' + self.name)
        print('Conditions: ' + str(self.conditions))
        print('Effects: ' + str(self.effects))
        print('<<<<<<<<<<<<<<<<<<<<<<<<')


    @classmethod
    def getActionStart(cls, action_name):
        for item in ActionStart.actionsList:
            if item.name == action_name:
                return item
        return None



class ActionEnd:

    actionsList = list()


    def __init__(self, grounded_action):
        name_act = grounded_action.name.split('#')
        name_act[0] = name_act[0] + '_end'
        self.grounded_action = grounded_action
        self.name = '#'.join(name_act)

        self.conditions = dict()
        for k, v in grounded_action.conditions.items():
            if k[:6] == 'at_end':
                self.conditions[k[7:]] = grounded_action.conditions[k]

        self.over_all_conditions = dict()
        for k, v in grounded_action.conditions.items():
            if k[:8] == 'over_all':
                self.over_all_conditions[k[9:]] = grounded_action.conditions[k]

        ### I don't think over all effects make sense
        # self.over_all_effects = dict()
        # for k, v in grounded_action.effects.items():
        #     if k[:8] == 'over_all':
        #         self.over_all_effects[k[9:]] = grounded_action.effects[k]

        self.effects = dict()
        for k, v in grounded_action.effects.items():
            if k[:6] == 'at_end':
                self.effects[k[7:]] = grounded_action.effects[k]

        ActionEnd.actionsList.append(self)


    def getPredicates(self):
        predicates_set = set()
        for k, v in self.conditions.items():
            for predicate in v:
                predicates_set.add('#'.join(predicate))
        for k, v in self.over_all_conditions.items():
            for predicate in v:
                predicates_set.add('#'.join(predicate))
        for k, v in self.effects.items():
            for predicate in v:
                predicates_set.add('#'.join(predicate))
        for k, v in self.over_all_effects.items():
            for predicate in v:
                predicates_set.add('#'.join(predicate))
        
        return predicates_set


    def printAction(self):
        print('>>>>>>>>>>>>>>>>>>>>>>>>')
        print('ActionEnd name: ' + self.name)
        print('Conditions: ' + str(self.conditions))
        print('Effects: ' + str(self.effects))
        print('Over all conditions: ' + str(self.over_all_conditions))
        print('Over all effects: ' + str(self.over_all_effects))
        print('<<<<<<<<<<<<<<<<<<<<<<<<')


    def getConditionPredicates(self):
        predicates_set = set()
        for k, v in self.conditions.items():
            for predicate in v:
                predicates_set.add('#'.join(predicate))
        
        return predicates_set


    def getOverAllPredicates(self):
        predicates_set = set()
        for k, v in self.over_all_conditions.items():
            for predicate in v:
                predicates_set.add('#'.join(predicate))
        
        return predicates_set


    def getEffectsPredicates(self):
        predicates_set = set()
        for k, v in self.effects.items():
            for predicate in v:
                predicates_set.add('#'.join(predicate))
        
        return predicates_set


    @classmethod
    def getActionEnd(cls, action_name):
        for item in ActionEnd.actionsList:
            if item.name == action_name:
                return item
        return None


    def getActionStart(self):
        name_act = self.grounded_action.name.split('#')
        name_act[0] = name_act[0] + '_start'
        name = '#'.join(name_act)
        return ActionStart.getActionStart(name)



def isPredicate(node_name):
    return len(node_name.split('%')) > 1


######### SIMPLIFY NAMES #########
def removeStartEndFromName(name):
    ''' Removes time from action name, works with or without parameters in name '''
    name1 = name.split('#')
    name2 = name1[0].split('_')
    del name2[-1]
    name3 = '_'.join(name2)
    params = '#'.join(name1[1:])
    if params:
        return name3+'#'+params
    return name3


def removeStartEndParamsFromName(name):
    name1 = removeStartEndFromName(name)
    return name1.split('#')[0]


#########    PRINTS     #########
def printNodesList(nodes_list, msg):
    names_list = list()
    for node in nodes_list:
        names_list.append(node.name)
    print(msg + str(names_list))


def printPlan(plan, action_times):
    print('>>> PRINTING PLAN')
    for i in action_times:
        print('> Time: ' + str(i))
        for action in ActionStart.getActionsWithTime(i):
            print(action.name)
        for action in ActionEnd.getActionsWithTime(i):
            print(action.name)
    print('---------------------------------')


######### WRITE TO FILE #########
def writePredicatesToFile(all_nodes):
    file = open('predicate_layers.txt', 'w')
    file.write('PREDICATE LAYERS:\n')
    for node_name in all_nodes:
        if isPredicate(node_name):
            file.write(node_name+'\n')
    # for layer_num in range(plan_length+1):
    #     file.write('>> Layer: ' + str(layer_num) + '\n')
    #     for predicate in all_predicates:
    #         file.write(predicate + '%' + str(layer_num) + '\n')
    #     file.write('----------------------------\n')
    file.close()


def writeParentsToFile(predicates_par_child):
    file = open('nodes_parents.txt', 'w')
    file.write('NODES AND PARENTS:\n')
    # For loop to print nodes in order
    for i in range(0, len(predicates_par_child.keys())):
        for predicate in predicates_par_child.keys():
            node_index = predicate.split('%')[1]
            if node_index == str(i):
                file.write('>>> Node: ' + predicate + '\n')
                for par in predicates_par_child[predicate]['parents']:
                    file.write(par + '\n')
                file.write('----------------------------\n')
    file.close()


def writeActionsToFile(actions_par_child):
    file = open('actions_par_child.txt', 'w')
    file.write('ACTIONS WITH CHILDREN AND PARENTS:\n')
    # This bigger for cycle is to print the actions in order
    for i in range(1, len(actions_par_child.keys())+1):
        for action_name in actions_par_child.keys():
            action_index = action_name.split('$')[1]
            if action_index == str(i):
                file.write('>>> ACTION: ' + action_name + '\n')
                file.write('> Parents:\n')
                for par in actions_par_child[action_name]['parents']:
                    file.write(par + '\n')
                file.write('> Children:\n')
                for child in actions_par_child[action_name]['children']:
                    file.write(child + '\n')
                file.write('----------------------------\n')
    file.close()


def writeNodesAndCPDsToFile(all_nodes, cpds_map):
    file = open('nodes_cpds.txt', 'w')
    file.write('NODES AND CPDs:\n')
    for node in all_nodes:
        file.write('>>> Node: ' + node + '\n')
        file.write(str(cpds_map[node]) + '\n')
    file.close()


######### NODE CHECKING #########
def checkNodesWithoutParents(parents):
    without_parents = False
    for node in parents.keys():
        first_layer = False
        if len(node.name.split('%')) > 1:
            if node.name.split('%')[1] == '0':
                first_layer = True
        if not first_layer and len(parents[node]) == 0:
            without_parents = True
            print('!!!! Node without parents !!!!')
            print('>> Node without parents: ' + node.name)
    if not without_parents:
        print('  No nodes without parents')


def checkNodesWithoutChildren(children, plan):
    without_children = False
    for node in children.keys():
        last_layer = False
        if len(node.name.split('%')) > 1:
            size = len(plan)
            if node.name.split('%')[1] == str(size):
                last_layer = True
        if not last_layer and len(children[node]) == 0:
            without_children = True
            print('!!!! Node without children !!!!')
            print('>> Node without children: ' + node.name)
    if not without_children:
        print('  No nodes without children')


def checkForRepeatedNodes(all_nodes):
    copy_set = set(all_nodes)
    if len(all_nodes) == len(copy_set):
        print('  No repeated nodes')
    else:
        print('!!! REPEATED NODES !!!')


######### CREATE ACTIONS #########
def createActions(operators):
    ''' Creates action instances for all actions in domain file '''
    for i in range(len(operators)):
        action_name = operators[i].name
        Action(action_name)


def createGroundedActions(original_plan):
    for action_name in original_plan:
        name = removeStartEndParamsFromName(action_name)
        if not Action.getAction(name):
            action = Action(name)
        else:
            action = Action.getAction(name)
        GroundedAction(action, action_name.split('#')[1:])


def cyclesRecurse(children, nodes_list, node):
    if len(children[node]) == 0:
        del nodes_list[-1]
        return True
    for child in children[node]:
        if child in nodes_list:
            printNodesList(nodes_list)
            print('>> Repeated node: ' + child.name)
            return False
        nodes_list.append(child)
        if not cyclesRecurse(children, nodes_list, child):
            return False
    del nodes_list[-1]
    return True


def checkCycles(all_nodes, children):
    for node in all_nodes:
        # children receives nodes and not strings, got to get node with this string as name
        nodes_list = list()
        nodes_list.append(node)
        for child in children[node]:
            if child in nodes_list:
                return False
            nodes_list.append(child)
            if not cyclesRecurse(children, nodes_list, child):
                return False
    return True


######### ADD PREDICATES #########
def addPredicate(predicate, predicates_par_child, all_nodes, layer_number):
    prev_pred_name = predicate + '%' + str(layer_number-1)
    parent_cpd = cpds_map[prev_pred_name]
    spont_false_true = pred_probabilities_map[predicate][0]
    spont_true_false = pred_probabilities_map[predicate][1]
    cpd = ConditionalProbabilityTable(
        [['T', 'T', 1-spont_true_false],
         ['T', 'F', spont_true_false],
         ['F', 'T', spont_false_true],
         ['F', 'F', 1-spont_false_true]], [parent_cpd]
    )
    pred_name = predicate+'%'+str(layer_number)
    cpds_map[pred_name] = cpd
    all_nodes.append(pred_name)
    predicates_par_child[pred_name] = dict()
    predicates_par_child[pred_name]['parents'] = set()
    predicates_par_child[pred_name]['children'] = set()
    predicates_par_child[pred_name]['parents'].add(prev_pred_name)
    predicates_par_child[prev_pred_name]['children'].add(pred_name)


def addPredicateLayer(predicates_set, layer_number, predicates_par_child, all_nodes):
    for predicate in predicates_set:
        predicate_name = predicate + '%' + str(layer_number)
        if not predicate_name in all_nodes:
            addPredicate(predicate, predicates_par_child, all_nodes, layer_number)


def addFirstLayerPredicates(predicates_set, all_nodes, predicates_par_child, initial_state):
    for predicate in predicates_set:
        pred_name = predicate + '%0'
        if predicate in initial_state:
            cpd = DiscreteDistribution({'T': 1, 'F': 0})
        else:
            cpd = DiscreteDistribution({'T': 0, 'F': 1})
        all_nodes.append(pred_name)
        cpds_map[pred_name] = cpd
        predicates_par_child[pred_name] = dict()
        predicates_par_child[pred_name]['parents'] = set()
        predicates_par_child[pred_name]['children'] = set()


######### CONNECT PREDICATES #########
def connectActionToConditionPredicates(action, action_name, predicates_par_child, actions_par_child, layer_number):
    for predicate in action.getConditionPredicates():
        pred_name = predicate + '%' + str(layer_number-1)
        # node_predicate = get_node(all_nodes, predicate + '%' + str(layer_number-1))
        # model.add_edge(node_predicate, action_node)
        predicates_par_child[pred_name]['children'].add(action_name)
        actions_par_child[action_name]['parents'].add(pred_name)


def connectActionToEffectsPredicates(action, action_name, all_nodes, predicates_par_child, actions_par_child, layer_number):
    index = 0
    for predicate in action.getEffectsPredicates():
        pred_name = predicate + '%' + str(layer_number)
        prev_pred_name = predicate + '%' + str(layer_number-1)
        spont_false_true = pred_probabilities_map[predicate][0]
        spont_true_false = pred_probabilities_map[predicate][1]
        name_without_time = removeStartEndFromName(action_name).split('$')[0]
        predicate_without_parameters = predicate.split('#')[0]
        effects_success = action_probabilities_map[name_without_time][1][predicate_without_parameters]
        action_cpd = cpds_map[action_name]
        parent_cpd = cpds_map[prev_pred_name]
        pred_cpd = ConditionalProbabilityTable(
            [['T', 'T', 'T', effects_success],
             ['T', 'T', 'F', 1-effects_success],
             ['T', 'F', 'T', 1-spont_true_false],
             ['T', 'F', 'F', spont_true_false],
             ['F', 'T', 'T', effects_success],
             ['F', 'T', 'F', 1-effects_success],
             ['F', 'F', 'T', spont_false_true],
             ['F', 'F', 'F', 1-spont_false_true]], [parent_cpd, action_cpd]
        )
        all_nodes.append(pred_name)
        cpds_map[pred_name] = pred_cpd
        predicates_par_child[pred_name] = dict()
        predicates_par_child[pred_name]['parents'] = set()
        predicates_par_child[pred_name]['children'] = set()
        # model.add_edge(action_node, node_predicate)
        predicates_par_child[pred_name]['parents'].add(action_name)
        actions_par_child[action_name]['children'].add(pred_name)
        predicates_par_child[pred_name]['parents'].add(prev_pred_name)
        predicates_par_child[prev_pred_name]['children'].add(pred_name)
        index = index + 1


def connectActionEndToActionStart(action, action_name, end_index, all_nodes, actions_par_child):
    action_start = action.getActionStart()
    # Search for the layer where actionStart is
    for j in range(1, end_index+1):
        action_start_name = action_start.name + '$' + str(j)
        if action_start_name in all_nodes:
            # Connecting ActionEnd to ActionStart
            actions_par_child[action_name]['parents'].add(action_start_name)
            actions_par_child[action_start_name]['children'].add(action_name)
            return j
    return 0


def connectActionToOverAllPredicates(action, action_name, start_index, end_index, actions_par_child, predicates_par_child):
    for predicate in action.getOverAllPredicates():
        for j in range(start_index, end_index):
            pred_name = predicate + '%' + str(j)
            actions_par_child[action_name]['parents'].add(pred_name)
            predicates_par_child[pred_name]['children'].add(action_name)


def addActionEdges(action, action_name, predicates_par_child, actions_par_child, layer_number, all_nodes):
    actions_par_child[action_name] = dict()
    actions_par_child[action_name]['parents'] = set()
    actions_par_child[action_name]['children'] = set()

    connectActionToConditionPredicates(action, action_name, predicates_par_child, actions_par_child, layer_number)
    connectActionToEffectsPredicates(action, action_name, all_nodes, predicates_par_child, actions_par_child, layer_number)

    if isinstance(action, ActionEnd):
        end_index = layer_number
        start_index = connectActionEndToActionStart(action, action_name, end_index, all_nodes, actions_par_child)
        # If action has no action_start then do not connect to over all predicates
        connectActionToOverAllPredicates(action, action_name, start_index, end_index, actions_par_child, predicates_par_child)


######### REMOVE NODES #########
def removeNode(node, all_nodes, actions_par_child, predicates_par_child, is_predicate):    
    if is_predicate:
        predicates_par_child.pop(node)
    else:
        actions_par_child.pop(node)

    all_nodes.remove(node)
    cpds_map.pop(node)

    for pred in predicates_par_child.keys():
        if node in predicates_par_child[pred]['parents']:
            predicates_par_child[pred]['parents'].remove(node)
        if node in predicates_par_child[pred]['children']:
            predicates_par_child[pred]['children'].remove(node)

    for action in actions_par_child.keys():
            if node in actions_par_child[action]['parents']:
                actions_par_child[action]['parents'].remove(node)
            if node in actions_par_child[action]['children']:
                actions_par_child[action]['children'].remove(node)


######### PRUNE NETWORK #########
def pruneNetwork(all_nodes, actions_par_child, predicates_par_child, goal):
    size = len(actions_par_child)
    goal_with_time = set()
    for item in goal:
        goal_with_time.add(item + '%' + str(size))

    for node in reversed(all_nodes):
        is_predicate = isPredicate(node)

        # print('>>> Node: ' + node)
        # if isPredicate:
        #     print('> Children: ' + str(predicates_par_child[node]['children']))
        #     print('> Parents: ' + str(predicates_par_child[node]['parents']))
        # else:
        #     print('> Children: ' + str(actions_par_child[node]['children']))
        #     print('> Parents: ' + str(actions_par_child[node]['parents']))

        if is_predicate:
            ##### Rule 1 #####
            # If predicate does not have children and is not the goal, then remove it
            if not node in goal_with_time:
                if not predicates_par_child[node]['children']:
                    removeNode(node, all_nodes, actions_par_child, predicates_par_child, is_predicate)
                    continue

            for action_name in actions_par_child.keys():

                ##### Rule 2 #####
                # If predicate is precondition of action_name then change its CPD to true
                if node in actions_par_child[action_name]['parents']:
                    cpds_map[node] = DiscreteDistribution({'T': 1, 'F': 0})
                    # remove edges to parents
                    for parent in predicates_par_child[node]['parents']:
                        if len(parent.split('%')) > 1:
                            predicates_par_child[parent]['children'].remove(node)
                        else:
                            actions_par_child[parent]['children'].remove(node)
                    predicates_par_child[node]['parents'] = set()
                
                ##### Rule 3 #####
                # If predicate is children of action_name, then remove edges from other parents
                ## Replace CPD
                if node in actions_par_child[action_name]['children']:
                    removed_parents = set()
                    for par in predicates_par_child[node]['parents']:
                        # if parent is predicate, then remove edges
                        if len(par.split('%')) > 1:
                            removed_parents.add(par)
                    # Had to remove it here and not inside the previous cycle because
                    ## I can't change the size of a list while iterating over it
                    for par in removed_parents:
                        predicates_par_child[par]['children'].remove(node)
                        predicates_par_child[node]['parents'].remove(par)
                    
                    action_name_no_time = removeStartEndFromName(action_name).split('$')[0]
                    predicate_no_parameters = node.split('#')[0]
                    effects_success = action_probabilities_map[action_name_no_time][1][predicate_no_parameters]
                    action_cpd = cpds_map[action_name]
                    # TODO: Check this table
                    cpds_map[node] = ConditionalProbabilityTable(
                                        [['T', 'T', effects_success],
                                         ['T', 'F', 1-effects_success],
                                         ['F', 'T', 0],
                                         ['F', 'F', 0]], [action_cpd])


######### BUILD NETWORK IN MODEL #########
def buildNetworkInModel(model, all_nodes, actions_par_child, predicates_par_child):
    nodes_dict = dict()
    for node_name in all_nodes:        
        cpd = cpds_map[node_name]
        node = Node(cpd, name=node_name)
        nodes_dict[node_name] = node
        model.add_node(node)

        if isPredicate(node_name):
            parents_dict = predicates_par_child
        else:
            parents_dict = actions_par_child
      
        for parent in parents_dict[node_name]['parents']:
            parent_node = nodes_dict[parent]
            model.add_edge(parent_node, node)


######### PARSE PLAN #########
def convertPlanToActionStart_End(original_plan):
    plan = list()
    for action_name in original_plan:
        name = removeStartEndFromName(action_name)
        # print("Name: " + name)
        grounded_action = GroundedAction.getGroundedAction(name)
        if action_name.split('#')[0][-5:] == 'start':
            action_start = ActionStart(grounded_action)
            plan.append(action_start)
        elif action_name.split('#')[0][-3:] == 'end':
            action_end = ActionEnd(grounded_action)
            plan.append(action_end)
    return plan


######### GET STUFF #########
# def getOnePlan(data):
#     global receivedPlan
#     global original_plan
#     if receivedPlan is False:
#         ordered_plan = data.esterel_plans[0].nodes

#         for item in ordered_plan:
#             name = str(item.name)  
#             # adds the action parameters to the name
#             for param in item.action.parameters:
#                 name = name + '#' + str(param.value)
#             original_plan.append(name)
        
#         receivedPlan = True


def getProbabilities():
    global pred_probabilities_map
    file = open('/home/tomas/ros_ws/src/ROSPlan/src/rosplan/rosplan_demos/rosplan_csp_exec_demo/probabilities.txt', 'r')
    line = file.readline()
    predicates = True
    actions_par_child = False
    while line:
        if line == '-\n':
            predicates = False
        elif predicates:
            split = line.split(' ')
            predicate = split[0]
            spont_false_true = float(split[1])
            spont_true_false = float(split[2].strip('\n'))
            pred_probabilities_map[predicate] = [spont_false_true, spont_true_false]
        else:
            split = line.split(' ')
            action = split[0]
            action_success = float(split[1])
            effects_success = dict()
            for i in range(2, len(split)):
                predicate = split[i].strip('\n').split('%')[0]
                probability = float(split[i].strip('\n').split('%')[1])
                effects_success[predicate] = probability
            action_probabilities_map[action] = [action_success, effects_success]
        line = file.readline()
    file.close()


def getElementsFromStateList(elements_list):
    elements_set = set()
    for element in elements_list:
        element_name = element.attribute_name
        for value in element.values:
            element_name = element_name + '#' + value.value
        elements_set.add(element_name)
    return elements_set


def getNodesLayers(nodes):
    nodes_layers = list()

    for node in nodes:
        if isPredicate(node):
            nodes_layers.append(node)
    
    return nodes_layers


# Gets everything needed to start building the network
def setupEverything():
    # print ("Waiting for service")
    rospy.wait_for_service('/rosplan_knowledge_base/domain/operators')
    rospy.wait_for_service('/rosplan_knowledge_base/domain/operator_details')

    # print ("Obtaining operators")
    domain_operators = rospy.ServiceProxy('/rosplan_knowledge_base/domain/operators', GetDomainOperatorService)

    # print('Obtaining goal')
    goals_list = rospy.ServiceProxy("/rosplan_knowledge_base/state/goals", GetAttributeService)().attributes
    goal = getElementsFromStateList(goals_list)

    # print('Obtaining initial state')
    initial_state_list = rospy.ServiceProxy('/rosplan_knowledge_base/state/propositions', GetAttributeService)().attributes
    initial_state = getElementsFromStateList(initial_state_list)

    # if testing:
    #     # Gets a totally-ordered plan from service
    #     # print('Obtaining plan')
    #     rospy.Subscriber("/csp_exec_generator/valid_plans", EsterelPlanArray, getOnePlan)
    #     while receivedPlan is False:
    #         continue
    #     print(original_plan)

    # print('Obtaining probabilities')
    getProbabilities()
    # print('   Predicates: ' + str(pred_probabilities_map))
    # print('   Actions: ' + str(action_probabilities_map))

    # print('Creating actions')
    operators = domain_operators().operators
    createActions(operators)

    return initial_state, goal


######### MAIN FUNCTION #########
## Builds, prunes and writes network to file
def handleRequest(req):

    original_plan = req.nodes


    initial_state, goal = setupEverything()
    # print("Initial state: " + str(initial_state))
    # print("Goal: " + str(goal))

    global returned_times

    createGroundedActions(original_plan)

    # print("Original plan: " + str(original_plan))
    # print("Actions: " + str(Action.getActionNamesList()))
    # print("Grounded actions: " + str(GroundedAction.getGroundedActionsList()))

    # Get plan as a list of ActionStart and ActionEnd's instances
    plan = convertPlanToActionStart_End(original_plan)

    predicates_set = set()
    all_nodes = list()
    # predicates_par_child is a dictionary where the key is the predicate's name and the value
    ## is another dictionary where the keys are 'parents' and 'children' and the values are sets
    predicates_par_child = dict()
    # same for actions_par_child
    actions_par_child = dict()

    for grounded_action in GroundedAction.actionsList:
        # Adds the predicates in the set grounded_action.getPredicates() to predicates_set
        predicates_set |= grounded_action.getPredicates()

    addFirstLayerPredicates(predicates_set, all_nodes, predicates_par_child, initial_state)

    layer_number = 1
    # Cycle which creates the entire Bayes Network until the end
    for action in plan:
        action_name = action.name + '$' + str(layer_number)
        success_prob = action_probabilities_map[removeStartEndFromName(action.name)][0]

        if isinstance(action, ActionStart):
            cpd = DiscreteDistribution({'T': success_prob, 'F': 1-success_prob})
        elif isinstance(action, ActionEnd):
            cpd = DiscreteDistribution({'T': 1, 'F': 0})
        cpds_map[action_name] = cpd

        all_nodes.append(action_name)
        addActionEdges(action, action_name, predicates_par_child, actions_par_child, layer_number, all_nodes)
        addPredicateLayer(predicates_set, layer_number, predicates_par_child, all_nodes)
        
        layer_number = layer_number + 1

    # print('>>> All nodes: \n' + str(all_nodes))
    pruneNetwork(all_nodes, actions_par_child, predicates_par_child, goal)

    model = BayesianNetwork()
    buildNetworkInModel(model, all_nodes, actions_par_child, predicates_par_child)
    model.bake()
    # model.plot()
    # plt.show()

    # print('Checking for repeated nodes')
    # checkForRepeatedNodes(all_nodes)
    # # print('Checking nodes without parents')
    # # checkNodesWithoutParents(parents)
    # # print('Checking nodes without children')
    # # checkNodesWithoutChildren(children, plan)
    # # print('Checking for cycles')
    # # if checkCycles(all_nodes, children):
    # #     print('  Network has no cycles')
    # # else:
    # #     print('!!! Network has cycles !!! ')
    # print('Writing predicates to file')
    # writePredicatesToFile(all_nodes)
    # print('Writing parents to file')
    # writeParentsToFile(predicates_par_child)
    # print('Writing actions_par_child to file')
    # writeActionsToFile(actions_par_child)
    # print('Writing nodes and CPDs to file')
    # writeNodesAndCPDsToFile(all_nodes, cpds_map)
    
    # print("All nodes: " + str(all_nodes))
    relevant_predicates = getNodesLayers(all_nodes)

    # size = len(plan)
    # distr_dict = dict()
    # for item in all_nodes:
    #     # If item is part of initial state then set it to true, else false
    #     if len(item.split('%')) > 1:
    #         if item.split('%')[1] == '0':
    #             if item.split('%')[0] in initial_state:
    #                 distr_dict[item] = 'T'
    #             else:
    #                 distr_dict[item] = 'F'
    # prob_distr = model.predict_proba([distr_dict])[0]

    # goal_distr = dict()
    # for item in goal:
    #     index = all_nodes.index(item + '%' + str(size))
    #     goal_distr[all_nodes[index]] = prob_distr[index]
    
    # print('\n\n>>> Goal distribution: ')
    # print(goal_distr)

    rospy.loginfo('Returned ' + str(returned_times))
    returned_times = returned_times + 1
    print('>>> Relevant predicates: ' + str(relevant_predicates))
    # TODO: It's just returning a number, it's not calculating the probability yet
    return CalculateProbabilityResponse(0.4, relevant_predicates)


######### SERVER INITIALISATION #########
def calculatePlanProbabilityServer():
    rospy.init_node('bayesian_network_calculator')
    s = rospy.Service('calculate_plan_probability', CalculateProbability, handleRequest)
    rospy.loginfo('** Bayesian network ready to receive plan **')
    rospy.spin()


if __name__ == "__main__":
    calculatePlanProbabilityServer()