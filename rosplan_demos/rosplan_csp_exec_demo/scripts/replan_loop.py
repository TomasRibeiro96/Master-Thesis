#!/usr/bin/env python
import rospkg
import rospy
import sys
import random

from std_srvs.srv import Empty, EmptyResponse, Trigger, TriggerResponse
from rosplan_dispatch_msgs.srv import DispatchService, DispatchServiceResponse
from rosplan_dispatch_msgs.srv import ExecAlternatives, ExecAlternativesResponse

import os


def run():

    rospy.init_node('coordinator', anonymous=False)

    # use or not adaptable plan dispatcher
    adaptable_plan_dispatcher_required = rospy.get_param('~adaptable_plan_dispatcher_required', True)
    if adaptable_plan_dispatcher_required:
        print 'using adaptable plan dispatcher'
    else:
        print 'NOT using adaptable plan dispatcher'

    # get execution type from param server
    execution_type = rospy.get_param('~execution_type', 'exec_type_not_set_')

    free_or_non_free = None
    if execution_type == 'iros_problems_free':
        free_or_non_free = 'free_'
    elif execution_type == 'iros_problems_deadlines':
        free_or_non_free = 'non_free_'

    # get execution type from param server
    problem_name = rospy.get_param('~problem_name', 'problem_name_not_set_')

    # for logging purposes, write results of the experiment to a file
    #ros_tcp_port = os.environ['ROS_MASTER_URI'].replace('http://localhost:', '')
    #if adaptable_plan_dispatcher_required:
        #log_file = open('exp_adaptable_' + free_or_non_free + problem_name + '_' + ros_tcp_port + '_n' + '.csv','w')
    #else:
        #log_file = open('exp_non_adaptable_' + free_or_non_free + problem_name + '_' + ros_tcp_port + '_n' + '.csv','w')
    #log_file.write('succeeded?, number of replans, number of executed actions\n')

    goal_achieved = False
    replans = 0


    while not goal_achieved and replans<10:
        rospy.wait_for_service('/rosplan_problem_interface/problem_generation_server')
        rospy.wait_for_service('/rosplan_planner_interface/planning_server')
        rospy.wait_for_service('/rosplan_parsing_interface/parse_plan')
        rospy.wait_for_service('/rosplan_plan_dispatcher/dispatch_plan')

        try:
            pg = rospy.ServiceProxy('/rosplan_problem_interface/problem_generation_server', Empty)
            pg()

            pi = rospy.ServiceProxy('/rosplan_planner_interface/planning_server', Empty)
            pi()

            pp = rospy.ServiceProxy('/rosplan_parsing_interface/parse_plan', Empty)
            pp()

            if(adaptable_plan_dispatcher_required):
                ea = rospy.ServiceProxy('/csp_exec_generator/gen_exec_alternatives', ExecAlternatives)
                ear = ea()

            dp = rospy.ServiceProxy('/rosplan_plan_dispatcher/dispatch_plan', DispatchService)
            dsr = dp()

            goal_achieved = dsr.goal_achieved
            if not dsr.goal_achieved:
                replans += 1

        except rospy.ServiceException, e:
            replans += 1

    # get number of executed actions
    number_of_executed_actions = 0
    try:
        ac = rospy.ServiceProxy('/action_count', Trigger)
        acr = ac()
        print 'Actions: ' + acr.message
        number_of_executed_actions = acr.message
    except rospy.ServiceException, e:
        print 0

    # check if goal was achieved, write to log file
    if goal_achieved:
        print 'REPLANS: ', str(replans)
        print 'SUCCESS '
        # log_file.write('1, ' + str(replans) + ', ' + str(number_of_executed_actions) + '\n')
    else:
        print 'REPLANS: ', str(replans)
        print 'FAILED '
        # log_file.write('0, ' + str(replans) + ', ' + str(number_of_executed_actions) + '\n')
    
    print('\n\n')
    # for logging purposes, write experiment results to text file, closing the file since we are done
    #log_file.close()


if __name__ == '__main__':
    run()
