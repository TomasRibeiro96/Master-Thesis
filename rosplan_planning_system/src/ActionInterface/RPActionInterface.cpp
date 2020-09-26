#include "rosplan_action_interface/RPActionInterface.h"
#include <iostream>
#include <fstream>
#include <iterator>
#include <map>

/* The implementation of RPMoveBase.h */
namespace KCL_rosplan {

	/* run action interface */
	void RPActionInterface::runActionInterface() {

		ros::NodeHandle nh("~");

		// set action name
		nh.getParam("pddl_action_name", params.name);

		// knowledge base services
		std::string kb = "knowledge_base";
		nh.getParam("knowledge_base", kb);

		// fetch action params
		std::stringstream ss;
		ss << "/" << kb << "/domain/operator_details";
		ros::service::waitForService(ss.str(),ros::Duration(20));
		ros::ServiceClient client = nh.serviceClient<rosplan_knowledge_msgs::GetDomainOperatorDetailsService>(ss.str());
		rosplan_knowledge_msgs::GetDomainOperatorDetailsService srv;
		srv.request.name = params.name;
		if(client.call(srv)) {
			params = srv.response.op.formula;
			op = srv.response.op;
		} else {
			ROS_ERROR("KCL: (RPActionInterface) could not call Knowledge Base for operator details, %s", params.name.c_str());
			return;
		}

		// collect predicates from operator description
		std::vector<std::string> predicateNames;

		// effects
		std::vector<rosplan_knowledge_msgs::DomainFormula>::iterator pit = op.at_start_add_effects.begin();
		for(; pit!=op.at_start_add_effects.end(); pit++)
			predicateNames.push_back(pit->name);

		pit = op.at_start_del_effects.begin();
		for(; pit!=op.at_start_del_effects.end(); pit++)
			predicateNames.push_back(pit->name);

		pit = op.at_end_add_effects.begin();
		for(; pit!=op.at_end_add_effects.end(); pit++)
			predicateNames.push_back(pit->name);

		pit = op.at_end_del_effects.begin();
		for(; pit!=op.at_end_del_effects.end(); pit++)
			predicateNames.push_back(pit->name);

		// simple conditions
		pit = op.at_start_simple_condition.begin();
		for(; pit!=op.at_start_simple_condition.end(); pit++)
			predicateNames.push_back(pit->name);

		pit = op.over_all_simple_condition.begin();
		for(; pit!=op.over_all_simple_condition.end(); pit++)
			predicateNames.push_back(pit->name);

		pit = op.at_end_simple_condition.begin();
		for(; pit!=op.at_end_simple_condition.end(); pit++)
			predicateNames.push_back(pit->name);

		// negative conditions
		pit = op.at_start_neg_condition.begin();
		for(; pit!=op.at_start_neg_condition.end(); pit++)
			predicateNames.push_back(pit->name);

		pit = op.over_all_neg_condition.begin();
		for(; pit!=op.over_all_neg_condition.end(); pit++)
			predicateNames.push_back(pit->name);

		pit = op.at_end_neg_condition.begin();
		for(; pit!=op.at_end_neg_condition.end(); pit++)
			predicateNames.push_back(pit->name);

		// fetch and store predicate details
		ss.str("");
		ss << "/" << kb << "/domain/predicate_details";
		ros::service::waitForService(ss.str(),ros::Duration(20));
		ros::ServiceClient predClient = nh.serviceClient<rosplan_knowledge_msgs::GetDomainPredicateDetailsService>(ss.str());
		std::vector<std::string>::iterator nit = predicateNames.begin();
		for(; nit!=predicateNames.end(); nit++) {
			if (predicates.find(*nit) != predicates.end()) continue;
			if (*nit == "=" || *nit == ">" || *nit == "<" || *nit == ">=" || *nit == "<=") continue;
			rosplan_knowledge_msgs::GetDomainPredicateDetailsService predSrv;
			predSrv.request.name = *nit;
			if(predClient.call(predSrv)) {
				if (predSrv.response.is_sensed){
					sensed_predicates.insert(std::pair<std::string, rosplan_knowledge_msgs::DomainFormula>(*nit, predSrv.response.predicate));	
				} else {
					predicates.insert(std::pair<std::string, rosplan_knowledge_msgs::DomainFormula>(*nit, predSrv.response.predicate));	
				}
			} else {
				ROS_ERROR("KCL: (RPActionInterface) could not call Knowledge Base for predicate details, %s", params.name.c_str());
				return;
			}
		}

		// create PDDL info publisher
		ss.str("");
		ss << "/" << kb << "/pddl_action_parameters";
		pddl_action_parameters_pub = nh.advertise<rosplan_knowledge_msgs::DomainFormula>(ss.str(), 10, true);

		// create the action feedback publisher
		std::string aft = "default_feedback_topic";
		nh.getParam("action_feedback_topic", aft);
		action_feedback_pub = nh.advertise<rosplan_dispatch_msgs::ActionFeedback>(aft, 10, true);

		// knowledge interface
		ss.str("");
		ss << "/" << kb << "/update_array";
		update_knowledge_client = nh.serviceClient<rosplan_knowledge_msgs::KnowledgeUpdateServiceArray>(ss.str());

		// listen for action dispatch
		std::string adt = "default_dispatch_topic";
		nh.getParam("action_dispatch_topic", adt);

        ros::SubscribeOptions ops;
        ops.template init<rosplan_dispatch_msgs::ActionDispatch>(adt, 1000, boost::bind(&KCL_rosplan::RPActionInterface::dispatchCallback, this, _1));
        ops.transport_hints = ros::TransportHints();
        ops.allow_concurrent_callbacks = true;
		ros::Subscriber ds = nh.subscribe(ops); // nh.subscribe(adt, 1000, &KCL_rosplan::RPActionInterface::dispatchCallback, this);

		// loop
		ros::Rate loopRate(1);
		ros::AsyncSpinner spinner(4);
        spinner.start();

		ROS_INFO("KCL: (%s) Ready to receive", params.name.c_str());

		while(ros::ok()) {
			pddl_action_parameters_pub.publish(params);
			loopRate.sleep();
		}
	}

	void RPActionInterface::printDispatchedActions(){
		std::stringstream ss;

		for(std::string action_name: actions_dispatched_){
			ss << " ";
			ss << action_name;
			ss << ",";
		}

		ROS_INFO("ISR: Actions dispatched: %s", ss.str().c_str());
	}

	bool RPActionInterface::startActionAlreadyExecuted(std::string action_name){
		for(std::string name: actions_dispatched_){
			if(name == action_name){
				return true;
			}
		}
		// std::map<std::string, rosplan_knowledge_msgs::DomainOperator>::iterator itr;
		// for( itr = actions_dispatched_.begin(); itr != actions_dispatched_.end(); ++itr){
		// 	if(action_name == itr->first){
		// 		return true;
		// 	}
		// }
		return false;
	}

	std::string RPActionInterface::getFullActionName(const rosplan_dispatch_msgs::ActionDispatch::ConstPtr& msg){
		std::stringstream full_action_name_ss;
		full_action_name_ss << msg->name;

		std::vector<diagnostic_msgs::KeyValue, std::allocator<diagnostic_msgs::KeyValue>> action_params = msg->parameters;

		for(diagnostic_msgs::KeyValue param: action_params){
			full_action_name_ss << " ";
			full_action_name_ss << param.value;
		}

		return full_action_name_ss.str();

	}

	// double RPActionInterface::getActionSuccessProb(std::string name){
	// 	ros::NodeHandle nh;
	// 	std::string prob_file_name = "~/ros_ws/src/ROSPlan/src/rosplan/factory_robot-probabilities/fac_rob-w3_p1.txt";

	// 	std::string line;
	// 	std::ifstream prob_file;
	// 	prob_file.open(prob_file_name);

	// 	bool inside_actions_probability = false;

	// 	ROS_INFO("ISR: Action name: %s", name.c_str());
	// 	if(prob_file.is_open()){
	// 		getline(prob_file, line);
	// 		ROS_INFO("ISR: getLine: %s", line.c_str());

	// 		while(getline(prob_file, line)){
	// 			ROS_INFO("ISR: Line: %s", line.c_str());
	// 			if(line == "-\n"){
	// 				inside_actions_probability = true;
	// 			}
	// 			if(inside_actions_probability){
	// 					std::string action = line.substr(0, line.find(" "));
	// 					ROS_INFO("ISR: Line inside: %s", action.c_str());
	// 					if(name == action){
	// 						line.erase(0, line.find(" ")+1);
	// 						line = line.substr(0, line.find(" "));

	// 						ROS_INFO("ISR: Got probability: %s", line.c_str());
	// 						return atof(line.c_str());
	// 					}
	// 			}
	// 		}
	// 	}
	// 	prob_file.close();
	// 	return 0;
	// }

	/* run action interface */
	void RPActionInterface::dispatchCallback(const rosplan_dispatch_msgs::ActionDispatch::ConstPtr& msg) {

		// check action name
		if(0==msg->name.compare("cancel_action")) {
            action_cancelled = true;
            return;
        }
		if(0!=msg->name.compare(params.name)) return;
		ROS_INFO("KCL: (%s) action received", params.name.c_str());

        action_cancelled = false;

		// check PDDL parameters
		std::vector<bool> found(params.typed_parameters.size(), false);
		std::map<std::string, std::string> boundParameters;
		for(size_t j=0; j<params.typed_parameters.size(); j++) {
			for(size_t i=0; i<msg->parameters.size(); i++) {
				if(params.typed_parameters[j].key == msg->parameters[i].key) {
					boundParameters[msg->parameters[i].key] = msg->parameters[i].value;
					found[j] = true;
					break;
				}
			}
			if(!found[j]) {
				ROS_INFO("KCL: (%s) aborting action dispatch; malformed parameters, missing %s", params.name.c_str(), params.typed_parameters[j].key.c_str());
				return;
			}
		}

		// send feedback (enabled)
		rosplan_dispatch_msgs::ActionFeedback fb;
		fb.action_id = msg->action_id;
		fb.status = "action enabled";
		action_feedback_pub.publish(fb);

		std::string full_action_name = getFullActionName(msg);

		bool start_action_executed = startActionAlreadyExecuted(full_action_name);

		// ROS_INFO("ISR: (%s) Full action name: %s", params.name.c_str(), full_action_name.c_str());
		// printDispatchedActions();

		// double success_prob = getActionSuccessProb(full_action_name);
		// double success_prob = 1;
		// double random_number = ((double) rand() / (RAND_MAX));
		// bool start_action_executed = false;

		// If action with this name is not in actions_dispatched_
		// then we are executing the start of that action
		// if((!start_action_executed) && (random_number<success_prob)){
		if(!start_action_executed){

			// ROS_INFO("ISR: (%s) Connecting action to at_start effects", params.name.c_str());

			// update knowledge base
			rosplan_knowledge_msgs::KnowledgeUpdateServiceArray updatePredSrv;
			
			// simple START del effects
			for(int i=0; i<op.at_start_del_effects.size(); i++) {

				std::map<std::string, rosplan_knowledge_msgs::DomainFormula>::iterator it = sensed_predicates.find(op.at_start_del_effects[i].name);
				if(it != sensed_predicates.end()) continue; // sensed predicate

				rosplan_knowledge_msgs::KnowledgeItem item;
				item.knowledge_type = rosplan_knowledge_msgs::KnowledgeItem::FACT;
				item.attribute_name = op.at_start_del_effects[i].name;
				item.values.clear();
				diagnostic_msgs::KeyValue pair;
				for(size_t j=0; j<op.at_start_del_effects[i].typed_parameters.size(); j++) {
					pair.key = predicates[op.at_start_del_effects[i].name].typed_parameters[j].key;
					pair.value = boundParameters[op.at_start_del_effects[i].typed_parameters[j].key];
					item.values.push_back(pair);
				}
				updatePredSrv.request.knowledge.push_back(item);
				updatePredSrv.request.update_type.push_back(rosplan_knowledge_msgs::KnowledgeUpdateService::Request::REMOVE_KNOWLEDGE);
			}

			// simple START add effects
			for(int i=0; i<op.at_start_add_effects.size(); i++) {

				std::map<std::string, rosplan_knowledge_msgs::DomainFormula>::iterator it = sensed_predicates.find(op.at_start_add_effects[i].name);
				if(it != sensed_predicates.end()) continue; // sensed predicate

				rosplan_knowledge_msgs::KnowledgeItem item;
				item.knowledge_type = rosplan_knowledge_msgs::KnowledgeItem::FACT;
				item.attribute_name = op.at_start_add_effects[i].name;
				item.values.clear();
				diagnostic_msgs::KeyValue pair;
				for(size_t j=0; j<op.at_start_add_effects[i].typed_parameters.size(); j++) {
					pair.key = predicates[op.at_start_add_effects[i].name].typed_parameters[j].key;
					pair.value = boundParameters[op.at_start_add_effects[i].typed_parameters[j].key];
					item.values.push_back(pair);
				}
				updatePredSrv.request.knowledge.push_back(item);
				updatePredSrv.request.update_type.push_back(rosplan_knowledge_msgs::KnowledgeUpdateService::Request::ADD_KNOWLEDGE);
			}

			if(updatePredSrv.request.knowledge.size()>0 && !update_knowledge_client.call(updatePredSrv))
				ROS_INFO("KCL: (%s) failed to update PDDL model in knowledge base", params.name.c_str());

			// actions_dispatched_.insert(std::pair<std::string, rosplan_knowledge_msgs::DomainOperator>(full_action_name, op));
			actions_dispatched_.push_back(full_action_name);

			// publish feedback (achieved)
			fb.status = "action achieved";
			action_feedback_pub.publish(fb);

		}
		// else if(random_number > success_prob){
		// 	ROS_INFO("ISR: (%s) Action failed", params.name.c_str());
		// 	return;
		// }
		
		// call concrete implementation
		// action_success = concreteCallback(msg);
		// action_success = true;
        // // ros::spinOnce();
        // if(action_cancelled) {
        //     action_success = false;
		// 	ROS_INFO("KCL: (%s) an old action that was cancelled is stopping now", params.name.c_str());
        //     return;
        // }

		else{
		// if(action_success){

			// ROS_INFO("ISR: (%s) Connecting action to at_end effects", params.name.c_str());
			// ROS_INFO("KCL: (%s) action completed successfully", params.name.c_str());

			// update knowledge base
			rosplan_knowledge_msgs::KnowledgeUpdateServiceArray updatePredSrv;

			// op = actions_dispatched_.at(full_action_name);

			// simple END del effects
			for(int i=0; i<op.at_end_del_effects.size(); i++) {

				std::map<std::string, rosplan_knowledge_msgs::DomainFormula>::iterator it = sensed_predicates.find(op.at_end_del_effects[i].name);
				if(it != sensed_predicates.end()) continue; // sensed predicate

				rosplan_knowledge_msgs::KnowledgeItem item;
				item.knowledge_type = rosplan_knowledge_msgs::KnowledgeItem::FACT;
				item.attribute_name = op.at_end_del_effects[i].name;
				item.values.clear();
				diagnostic_msgs::KeyValue pair;
				for(size_t j=0; j<op.at_end_del_effects[i].typed_parameters.size(); j++) {
					pair.key = predicates[op.at_end_del_effects[i].name].typed_parameters[j].key;
					pair.value = boundParameters[op.at_end_del_effects[i].typed_parameters[j].key];
					item.values.push_back(pair);
				}
				updatePredSrv.request.knowledge.push_back(item);
				updatePredSrv.request.update_type.push_back(rosplan_knowledge_msgs::KnowledgeUpdateService::Request::REMOVE_KNOWLEDGE);
			}

			// simple END add effects
			for(int i=0; i<op.at_end_add_effects.size(); i++) {

				std::map<std::string, rosplan_knowledge_msgs::DomainFormula>::iterator it = sensed_predicates.find(op.at_end_add_effects[i].name);
				if(it != sensed_predicates.end()) continue; // sensed predicate

				rosplan_knowledge_msgs::KnowledgeItem item;
				item.knowledge_type = rosplan_knowledge_msgs::KnowledgeItem::FACT;
				item.attribute_name = op.at_end_add_effects[i].name;
				item.values.clear();
				diagnostic_msgs::KeyValue pair;
				for(size_t j=0; j<op.at_end_add_effects[i].typed_parameters.size(); j++) {
					pair.key = predicates[op.at_end_add_effects[i].name].typed_parameters[j].key;
					pair.value = boundParameters[op.at_end_add_effects[i].typed_parameters[j].key];
					item.values.push_back(pair);
				}
				updatePredSrv.request.knowledge.push_back(item);
				updatePredSrv.request.update_type.push_back(rosplan_knowledge_msgs::KnowledgeUpdateService::Request::ADD_KNOWLEDGE);
			}

			if(updatePredSrv.request.knowledge.size()>0 && !update_knowledge_client.call(updatePredSrv))
				ROS_INFO("KCL: (%s) failed to update PDDL model in knowledge base", params.name.c_str());

			// publish feedback (achieved)
			fb.status = "action achieved";
			action_feedback_pub.publish(fb);

		}
	}

} // close namespace
