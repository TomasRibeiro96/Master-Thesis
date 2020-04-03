#!/usr/bin/env python

import sys
import rospy
from rosplan_knowledge_msgs.srv import *
from rosplan_knowledge_msgs.msg import *
from rosplan_dispatch_msgs.msg import EsterelPlanArray
from rosplan_dispatch_msgs.msg import EsterelPlan
import matplotlib
import matplotlib.pyplot as plt
from numpy import *
from pomegranate import *
import collections



class Action:

    # Class parameter with all actions
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


    def getConditionPredicates(self):
        predicates_set = set()
        for k, v in self.conditions.items():
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



''' Creates action instances for all actions in domain file '''
def create_actions(operators):
    for i in range(len(operators)):
        action_name = operators[i].name
        Action(action_name)


def write_predicates_to_file(plans_info):
    file = open('predicate_layers.txt', 'w')
    file.write('PREDICATE LAYERS:\n')
    i = 0
    for plan_info in plans_info:
        file.write('\n>>>>>>>>>> PLAN ' + str(i) + ' <<<<<<<<<<\n')
        for layer_num in range(len(plan_info['plan'])):
            file.write('>> Layer: ' + str(layer_num) + '\n')
            for predicate in plan_info['all_predicates']:
                file.write(predicate + '%' + str(layer_num) + '\n')
            file.write('----------------------------\n')
        file.write('\n/////////////////////////////////\n')
        i = i + 1
    file.close()


def write_parents_to_file(plans_info):
    file = open('nodes_parents.txt', 'w')
    file.write('NODES AND PARENTS:\n')
    plan_num = 0
    for plan_info in plans_info:
        file.write('\n>>>>>>>>>> PLAN ' + str(plan_num) + ' <<<<<<<<<<\n')
        for node in plan_info['parents'].keys():
            file.write('>>> Node: ' + node.name + '\n')
            for par in plan_info['parents'][node]:
                file.write(par.name + '\n')
            file.write('----------------------------\n')
        file.write('\n/////////////////////////////////\n')
        plan_num = plan_num + 1
    file.close()


def write_actions_to_file(plans_info):
    file = open('actions_par_child.txt', 'w')
    file.write('ACTIONS WITH CHILDREN AND PARENTS:\n')
    i = 0
    for plan_info in plans_info:
        file.write('\n>>>>>>>>>> PLAN ' + str(i) + ' <<<<<<<<<<\n')
        for action in plan_info['actions'].keys():
            file.write('>>> ACTION: ' + action.name + '\n')
            file.write('> Parents:\n')
            for par in plan_info['actions'][action]['parents']:
                file.write(par.name + '\n')
            file.write('> Children:\n')
            for child in plan_info['actions'][action]['children']:
                file.write(child.name + '\n')
            file.write('----------------------------\n')
        file.write('\n/////////////////////////////////\n')
        i = i + 1
    file.close()


def check_nodes_without_parents(plans_info):
    plan_num = 0
    without_parents = False
    for plan_info in plans_info:
        for node in plan_info['parents'].keys():
            first_layer = False
            if len(node.name.split('%')) > 1:
                if node.name.split('%')[1] == '0':
                    first_layer = True
            if not first_layer and len(plan_info['parents'][node]) == 0:
                without_parents = True
                print('!!!! Node without parents !!!!')
                print('>> Plan: ' + str(plan_num))
                print('>> Node without parents: ' + node.name)
        plan_num = plan_num + 1
    
    if not without_parents:
        print('  No nodes without parents')


def check_nodes_without_children(plans_info):
    plan_num = 0
    without_children = False
    for plan_info in plans_info:
        for node in plan_info['children'].keys():
            last_layer = False
            if len(node.name.split('%')) > 1:
                size = len(plan_info['plan'])
                if node.name.split('%')[1] == str(size):
                    last_layer = True
            if not last_layer and len(plan_info['children'][node]) == 0:
                without_children = True
                print('!!!! Node without children !!!!')
                print('>> Plan: ' + str(plan_num))
                print('>> Node without children: ' + node.name)
        plan_num = plan_num + 1

    if not without_children:
        print('  No nodes without children')


def print_nodes_list(nodes_list):
    names_list = list()
    for node in nodes_list:
        names_list.append(node.name)
    print(names_list)


def cycles_recurse(plans_info, plan_num, nodes_list, node):
    plan_info = plans_info[plan_num]
    if len(plan_info['children'][node]) == 0:
        del nodes_list[-1]
        return True
    for child in plan_info['children'][node]:
        if child in nodes_list:
            print_nodes_list(nodes_list)
            print('>> Repeated node: ' + child.name)
            print('>> Plan number: ' + str(plan_num))
            return False
        nodes_list.append(child)
        if not cycles_recurse(plans_info, plan_num, nodes_list, child):
            return False
    del nodes_list[-1]
    return True


def check_cycles(plans_info):
    plan_num = 0
    for plan_info in plans_info:
        for node in plan_info['all_predicates']:
            # children receives nodes and not strings, got to get node with this string as name
            node = get_node(plan_info['all_nodes'], node+'%0')
            nodes_list = list()
            nodes_list.append(node)
            for child in plan_info['children'][node]:
                if child in nodes_list:
                    return False
                nodes_list.append(child)
                if not cycles_recurse(plans_info, plan_num, nodes_list, child):
                    return False
        plan_num = plan_num + 1
    return True


def waiting_for_services(operator_service, operator_details_service):
    rospy.wait_for_service(operator_service)
    rospy.wait_for_service(operator_details_service)


def print_plan(plan, action_times):
    print('>>> PRINTING PLAN')
    for i in action_times:
        print('> Time: ' + str(i))
        for action in ActionStart.getActionsWithTime(i):
            print(action.name)
        for action in ActionEnd.getActionsWithTime(i):
            print(action.name)
    print('---------------------------------')


def get_node(all_nodes, name):
        for node in all_nodes:
            if node.name == name:
                return node
        # for node in self.all_nodes:
        #     print('*** ' + node.name)
        # print('>>> ' + name)
        return None


class Graph(object): ## CLASS TO GENERATE The Dynamic bayes network and to find the probability of success of an plan.
    

    def __init__(self):         ####constructor  method initialize the object
        # self.plans_info = list of dictionaries
        self.plans_info = list()
        self.received=False

    ''' TODO: Why is this callback being executed 2 times? '''
    def total_plan(self, data): ##### call back for the the total order plans from oscar.
        # If condition keeps the callback from running 2 times
        if not self.received:
            # data.esterel_plans is a list of all the totally-ordered plans

            for ordered_plan in data.esterel_plans:

                total_plan = ordered_plan.nodes

                plan = list()
                grounded_actions_set = set()
                
                for item in total_plan:
                    name = item.action.name
                    action = Action.getAction(name)
                    
                    param_list = list()
                    for param in item.action.parameters:
                        param_list.append(param.value)
                    
                    
                    # Gets grounded action if it already exists
                    grounded_action = GroundedAction.getGroundedAction(name)
                    # If grounded action does not exist then it creates a new one
                    if grounded_action == None:
                        grounded_action = GroundedAction(action, param_list)

                    grounded_actions_set.add(grounded_action)
                    
                    if item.name[-5:] == 'start':
                        node = ActionStart(grounded_action)
                    elif item.name[-3:] == 'end':
                        node = ActionEnd(grounded_action)
                    
                    plan.append(node)
                
                plan_info = collections.OrderedDict()
                # list of actions
                plan_info['plan'] = plan
                # set of grounded actions
                plan_info['grounded_actions'] = grounded_actions_set
                plan_info['model'] = BayesianNetwork()
                # set of nodes
                plan_info['all_nodes'] = set()
                # dictionary where the values are the parent of a node (key)
                plan_info['parents'] = collections.OrderedDict()
                # dictionary where the values are the children of a node (key)
                plan_info['children'] = collections.OrderedDict()
                # dictionary where the key is an action and the value is another 
                ## dictionary. In this one, there are two keys 'parents' and 'children'
                ### their values are a set of nodes
                plan_info['actions'] = collections.OrderedDict()
                # set of predicates (strings)
                plan_info['all_predicates'] = set()

                self.plans_info.append(plan_info)

            self.received=True


    def call_service(self):

        print ("Waiting for service")
        rospy.wait_for_service('/rosplan_knowledge_base/domain/operators')
        rospy.wait_for_service('/rosplan_knowledge_base/domain/operator_details')
        
        print ("Calling Service")
        domain_operators = rospy.ServiceProxy('/rosplan_knowledge_base/domain/operators', GetDomainOperatorService)

        print('Creating actions')
        operators = domain_operators().operators
        create_actions(operators)

        #### Subscribing to the node to get the total order plans ######################
        rospy.Subscriber("/csp_exec_generator/valid_plans", EsterelPlanArray, self.total_plan)

        print('Parsing plan')
        while self.received is False:
            continue

        print('Building bayesian networks for {} totally-ordered plans'.format(len(self.plans_info)))
        # for loop over each plan
        for plan_info in self.plans_info:
            plan = plan_info['plan']

            cpd = DiscreteDistribution({'T': 1, 'F': 0})

            for grounded_action in plan_info['grounded_actions']:
                # Adds the predicates in the set grounded_action.getPredicates() to predicates_set
                plan_info['all_predicates'] |= grounded_action.getPredicates()
            predicates_set = plan_info['all_predicates']
            
            # Adding first layer of predicates
            for predicate in predicates_set:
                node = Node(cpd, name=predicate + '%0')
                plan_info['all_nodes'].add(node)
                plan_info['children'][node] = set()
                plan_info['parents'][node] = set()
                plan_info['model'].add_node(node)

            layer_number = 1
            # Cycle which creates the entire Bayes Network until the end
            for action in plan:
                # Add predicate layer
                for predicate in predicates_set:
                    node = Node(cpd, name = predicate + '%' + str(layer_number))
                    plan_info['all_nodes'].add(node)
                    plan_info['model'].add_node(node)
                    plan_info['parents'][node] = set()
                    plan_info['children'][node] = set()
                    plan_info['parents'][node].add(get_node(plan_info['all_nodes'], predicate + '%' + str(layer_number-1)))
                    plan_info['children'][get_node(plan_info['all_nodes'], predicate + '%' + str(layer_number-1))].add(node)
                    plan_info['model'].add_edge(get_node(plan_info['all_nodes'], predicate + '%' + str(layer_number-1)), node)
    
                # Add action
                action_node = Node(cpd, name = action.name + '$' + str(layer_number))
                plan_info['model'].add_node(action_node)
                plan_info['all_nodes'].add(action_node)

                # Initialise stuff so I can save a node's parents and an action's parents and children
                plan_info['parents'][action_node] = set()
                plan_info['children'][action_node] = set()
                plan_info['actions'][action_node] = dict()
                plan_info['actions'][action_node]['parents'] = set()
                plan_info['actions'][action_node]['children'] = set()
                # Connecting to condition predicates
                for predicate in action.getConditionPredicates():
                    node_predicate = get_node(plan_info['all_nodes'], predicate + '%' + str(layer_number-1))
                    plan_info['model'].add_edge(node_predicate, action_node)
                    plan_info['parents'][action_node].add(node_predicate)
                    plan_info['children'][node_predicate].add(action_node)
                    plan_info['actions'][action_node]['parents'].add(node_predicate)
                # Connecting to effects predicates
                for predicate in action.getEffectsPredicates():
                    node_predicate = get_node(plan_info['all_nodes'], predicate + '%' + str(layer_number))
                    plan_info['model'].add_edge(action_node, node_predicate)
                    plan_info['parents'][node_predicate].add(action_node)
                    plan_info['children'][action_node].add(node_predicate)
                    plan_info['actions'][action_node]['children'].add(node_predicate)

                if isinstance(action, ActionEnd):
                    end_index = layer_number
                    action_start = action.getActionStart()
                    for j in range(layer_number):
                        if get_node(plan_info['all_nodes'], action_start.name + '$' + str(j)):
                            action_start_node = get_node(plan_info['all_nodes'], action_start.name + '$' + str(j))
                            # Connecting ActionEnd to ActionStart
                            plan_info['model'].add_edge(action_start_node, action_node)
                            plan_info['parents'][action_node].add(action_start_node)
                            plan_info['children'][action_start_node].add(action_node)
                            plan_info['actions'][action_node]['parents'].add(action_start_node)
                            plan_info['actions'][action_start_node]['children'].add(action_node)
                            start_index = j
                            break
                    # Connecting to over all predicates
                    for predicate in action.getOverAllPredicates():
                        # Had to add one because the last index is exclusive
                        for j in range(start_index+1, end_index):
                            node = get_node(plan_info['all_nodes'], predicate + '%' + str(j))
                            plan_info['model'].add_edge(node, action_node)
                            plan_info['parents'][action_node].add(node)
                            plan_info['children'][node].add(action_node)
                            plan_info['actions'][action_node]['parents'].add(node)
                
                layer_number = layer_number + 1

                ## Commented this line so the code runs faster
                # plan_info['model'].bake()

        print('Writing predicates to file')
        write_predicates_to_file(self.plans_info)
        print('Writing parents to file')
        write_parents_to_file(self.plans_info)
        print('Writing actions to file')
        write_actions_to_file(self.plans_info)
        print('Checking nodes without parents')
        check_nodes_without_parents(self.plans_info)
        print('Checking nodes without children')
        check_nodes_without_children(self.plans_info)
        print('Checking for cycles')
        if check_cycles(self.plans_info):
            print('  Network has no cycles')
        else:
            print('!!! Network has cycles !!! ')

        # print_plan(self.plan, self.action_times)

        print('>>> Execution finished <<<')

        # self.plans_info[0]['model'].plot()
        # plt.show()

        # rospy.spin()



if __name__ == "__main__":

    rospy.init_node('query_client_node', anonymous=True)
    Graph().call_service()
   
    # sys.exit(1)
