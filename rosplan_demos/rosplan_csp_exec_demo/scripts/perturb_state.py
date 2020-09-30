#!/usr/bin/env python
import rospkg
import rospy
import sys
import random

from rosplan_knowledge_msgs.srv import KnowledgeUpdateServiceArray, KnowledgeUpdateServiceArrayResponse, KnowledgeUpdateServiceArrayRequest, KnowledgeQueryService, KnowledgeQueryServiceResponse, KnowledgeQueryServiceRequest, GetDomainAttributeService, GetDomainAttributeServiceRequest, GetDomainAttributeServiceResponse, PerturbStateService, PerturbStateServiceResponse, GetAttributeService, GetAttributeServiceRequest, GetAttributeServiceResponse
from rosplan_knowledge_msgs.msg import KnowledgeItem
from diagnostic_msgs.msg import KeyValue

import os

pred_probabilities_map_ = dict()

predicates_list_ = list()


def getProbabilities():
    global pred_probabilities_map_
    
    prob_file_path = rospy.get_param('~probabilities_file')
    file = open(prob_file_path, 'r')
    line = file.readline()
    predicates = True
    while line:
        if line == '-\n':
            predicates = False
        elif predicates:
            split = line.split(' ')
            predicate = split[0]
            spont_false_true = float(split[1])
            spont_true_false = float(split[2].strip('\n'))
            pred_probabilities_map_[predicate] = [spont_false_true, spont_true_false]
        line = file.readline()
    file.close()


def getListOfAllPredicates():
    global predicates_list_

    prop_serv = rospy.ServiceProxy('/rosplan_knowledge_base/domain/predicates', GetDomainAttributeService)
    prop_req = GetDomainAttributeServiceRequest()
    predicates_list_ = prop_serv(prop_req).items

    # rospy.loginfo('ISR: (%s) Predicates list:\n%s', rospy.get_name(), str(predicates_list_))


def getPredicateKnowledgeItem(predicate):
    predicate_name = predicate.split('#')[0]
    values = predicate.split('#')[1:]

    # rospy.loginfo('ISR: (/perturb_server) Predicate: ' + str(predicate))
    # rospy.loginfo('ISR: (/perturb_server) Predicate name: ' + str(predicate_name))
    # rospy.loginfo('ISR: (/perturb_server) Values: ' + str(values))

    ki = KnowledgeItem()
    ki.knowledge_type = ki.FACT
    ki.is_negative = False
    ki.attribute_name = predicate_name
    ki_values = list()

    i = 0

    for pred in predicates_list_:
        if pred.name == predicate_name:
            for kv in pred.typed_parameters:
                key_value = KeyValue()
                key_value.key = kv.key
                key_value.value = values[i]
                ki_values.append(key_value)
                i = i + 1
            break

    ki.values = ki_values

    return ki


def perturb(req):

    # rospy.loginfo('ISR: (%s) Starting to perturb', rospy.get_name())
    # rospy.loginfo('Predicates: ' + str(pred_probabilities_map_.keys()))

    for predicate in pred_probabilities_map_.keys():
        spont_false_true = pred_probabilities_map_[predicate][0]
        spont_true_false = pred_probabilities_map_[predicate][1]

        # Service to add or remove fact to knowledge base
        update_serv = rospy.ServiceProxy('/rosplan_knowledge_base/update_array', KnowledgeUpdateServiceArray)
        update_req = KnowledgeUpdateServiceArrayRequest()

        # Service to check whether a fact is already in the knowledge base or not (whether it is in the current state)
        queryKB = rospy.ServiceProxy('/rosplan_knowledge_base/query_state', KnowledgeQueryService)
        query_KB_req = KnowledgeQueryServiceRequest()

        ki = getPredicateKnowledgeItem(predicate)
        query_KB_req.knowledge.append(ki)

        query_KB_resp = queryKB(query_KB_req)
        is_fact_in_KB = query_KB_resp.results[0]

        number = random.random()

        # If fact is not in KB (is False) then add it to
        # the KB with a probability of spont_false_true
        if not is_fact_in_KB and number < spont_false_true:
            # rospy.loginfo('ISR: (%s) Adding ' + predicate + ' to KB', rospy.get_name())
            ki.is_negative = False
            update_req.knowledge.append(ki)
            update_req.update_type = [0]
            update_successful = update_serv(update_req)
            # rospy.loginfo('ISR: (%s) Update successful: %s', rospy.get_name(), str(update_successful))


        # If fact is in KB (is True) then remove it from
        # the KB with a probability of spont_true_false
        elif is_fact_in_KB and number < spont_true_false:
            # rospy.loginfo('ISR: (%s) Removing ' + predicate + ' from KB', rospy.get_name())
            update_req.update_type = [2]
            update_req.knowledge.append(ki)
            update_successful = update_serv(update_req)
            # rospy.loginfo('ISR: (%s) Update successful: %s', rospy.get_name(), str(update_successful))
    
        # state = getProp_srv(getProp_req)
        # rospy.loginfo('ISR: (%s) State after perturbation:\n%s', rospy.get_name(), str(state.attribtues))

    return PerturbStateServiceResponse(True)


if __name__ == '__main__':
    rospy.init_node('perturb_state_server')

    # rospy.loginfo('ISR: (/perturb_server) Waiting for services')
    rospy.wait_for_service('/rosplan_knowledge_base/domain/predicates')
    rospy.wait_for_service('/rosplan_knowledge_base/update_array')
    rospy.wait_for_service('/rosplan_knowledge_base/query_state')
    rospy.wait_for_service('/rosplan_knowledge_base/state/propositions')

    getProbabilities()
    getListOfAllPredicates()

    rospy.Service('perturb_state', PerturbStateService, perturb)

    # rospy.loginfo('ISR: (%s) Spinning', , rospy.get_name())

    rospy.spin()
