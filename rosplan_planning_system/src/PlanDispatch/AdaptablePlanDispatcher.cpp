#include "rosplan_planning_system/PlanDispatch/AdaptablePlanDispatcher.h"
#include <unistd.h>

namespace KCL_rosplan {

	/*-------------*/
	/* constructor */
	/*-------------*/

	AdaptablePlanDispatcher::AdaptablePlanDispatcher(ros::NodeHandle& nh): display_edge_type_(false),
        PlanDispatcher(nh)  {

		node_handle = &nh;

		ros::NodeHandle nh_;
		perturb_client_ = nh_.serviceClient<rosplan_knowledge_msgs::PerturbStateService>("perturb_state");

		std::string plan_graph_topic = "plan_graph";
		nh.getParam("plan_graph_topic", plan_graph_topic);
		plan_graph_publisher = node_handle->advertise<std_msgs::String>(plan_graph_topic, 1000, true);

        gen_alternatives_client = node_handle->serviceClient<rosplan_dispatch_msgs::ExecAlternatives>("/csp_exec_generator/gen_exec_alternatives");

		// display edge type with colors (conditional edge, interference edge, etc)
		nh.param("display_edge_type", display_edge_type_, false);

		need_to_replan = false;

		reset();
	}

	AdaptablePlanDispatcher::~AdaptablePlanDispatcher()
	{

	}

	void AdaptablePlanDispatcher::reset() {
		PlanDispatcher::reset();
        actions_executing.clear();
		finished_execution = true;
	}

	/*-------------------*/
	/* Plan subscription */
	/*-------------------*/

	void AdaptablePlanDispatcher::planCallback(const rosplan_dispatch_msgs::EsterelPlanArray plan) {
		// ROS_INFO("ISR: (%s) Inside planCallback", ros::this_node::getName().c_str());
		if(plan.plan_success_prob.size() != plan.esterel_plans.size()) {
			ROS_WARN("KCL: (%s) Plans received, but probabilities array of different size. Ignoring.", ros::this_node::getName().c_str());
			replan_requested = true;
			return;
		}
		if(plan.esterel_plans.size() == 0) {
			ROS_WARN("KCL: (%s) Zero plans received in message.", ros::this_node::getName().c_str());
			replan_requested = true;
			return;
		}
		float bestProb = plan.plan_success_prob[0];
		current_plan = plan.esterel_plans[0];

		current_plan = plan.esterel_plans.back();
		bestProb = plan.plan_success_prob.back();
		// for(int i=1; i<plan.plan_success_prob.size(); i++) {
		// 	if(plan.plan_success_prob[i] > bestProb) {
		// 		// highest probability
		// 		bestProb = plan.plan_success_prob[i];
		// 		current_plan = plan.esterel_plans[i];
		// 	} else if(plan.plan_success_prob[i] == bestProb && current_plan.nodes.size() < plan.esterel_plans[i].nodes.size()) { 
		// 		// break ties on number of actions
		// 		current_plan = plan.esterel_plans[i];
		// 	}
		// }

/*            std::vector<int> ac;
            for(int i=0; i<actions_executing.size(); i++) {
                if(action_completed[actions_executing[i]]) ac.push_back(actions_executing[i]);
            }
            initialise();
            for(int i=0; i<actions_executing.size(); i++) {
                
                action_dispatched[actions_executing[i]] = true;
                action_received[actions_executing[i]] = true;
                action_completed[actions_executing[i]] = (std::find(ac.begin(), ac.end(), actions_executing[i]) != ac.end());
            }
*/


		    for(std::vector<rosplan_dispatch_msgs::EsterelPlanEdge>::const_iterator ci = current_plan.edges.begin(); ci != current_plan.edges.end(); ci++) {
			    edge_active[ci->edge_id] = false;
		    }

			// ROS_INFO("KCL: (%s) Plan selected with probability %f.", ros::this_node::getName().c_str(), bestProb);
			plan_received = true;
			// printPlan();
//		} else {
//			ROS_INFO("KCL: (%s) Plan received, but current execution not yet finished.", ros::this_node::getName().c_str());
//		}
	}

	void AdaptablePlanDispatcher::perturbWorldState(){
		//// Perturb state
		rosplan_knowledge_msgs::PerturbStateService srv;
		ROS_INFO("ISR: (%s) Perturbing world state", ros::this_node::getName().c_str());
		if(perturb_client_.call(srv)){
			if(srv.response.success){
				// ROS_INFO("ISR: (%s) Successfully perturbed state", ros::this_node::getName().c_str());
			}
			else{
				// ROS_INFO("ISR: (%s) Something went wrong while perturbing", ros::this_node::getName().c_str());
			}
		}
		else{
			ROS_INFO("ISR: (%s) Did NOT perturb state", ros::this_node::getName().c_str());
		}

	}

	std::string AdaptablePlanDispatcher::getFullActionName(rosplan_dispatch_msgs::EsterelPlanNode node){
		std::stringstream ss;

		ss << node.action.name;

		if(node.node_type == node.ACTION_START){
			ss << "_start";
		}
		else{
			ss << "_end";
		}

		std::vector<diagnostic_msgs::KeyValue, std::allocator<diagnostic_msgs::KeyValue>> parameters = node.action.parameters;
		for(diagnostic_msgs::KeyValue param: parameters){
			ss << "#";
			ss << param.value;
		}

		return ss.str();
	}

	void AdaptablePlanDispatcher::printEsterelPlan(){
		std::stringstream ss;

		for(std::vector<rosplan_dispatch_msgs::EsterelPlanNode>::const_iterator ci = current_plan.nodes.begin(); ci != current_plan.nodes.end(); ci++) {

			rosplan_dispatch_msgs::EsterelPlanNode node = *ci;

			if(ci != current_plan.nodes.begin()){
				ss << ", ";
			}
			ss << getFullActionName(node);
		}

		ROS_INFO("ISR: (%s) Esterel plan: %s", ros::this_node::getName().c_str(), ss.str().c_str());

	}

	void AdaptablePlanDispatcher::removeNextActionFromCompletedAndDispatched(std::string action_name){

		int action_id = map_node_id[action_name];

		std::string name_no_params = action_name.substr(0, action_name.find("#"));
		std::size_t pos = 0;
		while((pos = name_no_params.find("_")) != std::string::npos){
			// 1 is because the length of "_" is 1
			name_no_params.erase(0, pos + 1);
		}
		// ROS_INFO("ISR: (%s) Time: %s", ros::this_node::getName().c_str(), name_no_params.c_str());

		// ROS_INFO("ISR: (%s) Removing node from Dispatched/Completed: %s %d", ros::this_node::getName().c_str(), action_name.c_str(), action_id);

		if(name_no_params == "start"){
			ROS_INFO("ISR: (%s) Removing from action dispatched: %s %d", ros::this_node::getName().c_str(), action_name.c_str(), action_id);
			action_dispatched[action_id] = false;
		}
		else if(name_no_params == "end"){
			ROS_INFO("ISR: (%s) Removing from action completed: %s %d", ros::this_node::getName().c_str(), action_name.c_str(), action_id);
			action_completed[action_id] = true;
		}

		// ROS_INFO("ISR: (%s) Removed from Dispatched/Completed: %s %d", ros::this_node::getName().c_str(), action_name.c_str(), action_id);
	}

	void AdaptablePlanDispatcher::printMap(std::map<int,bool> m, std::string msg){
		std::stringstream ss;
		for (auto const& pair: m) {
			std::string second = pair.second ? "True" : "False";
			ss << "\n{" << pair.first << ": " << second << "}";
		}
		ROS_INFO("ISR: (%s)\nMap of %s: %s", ros::this_node::getName().c_str(), msg.c_str(), ss.str().c_str());
	}

	void AdaptablePlanDispatcher::printVectorInts(std::vector<int> v, std::string msg){
		std::stringstream ss;
		for(std::vector<int>::iterator it = v.begin(); it != v.end(); it++){
			if(it != v.begin()){
				ss << ", ";
			}
			ss << *it;
		}
		ROS_INFO("ISR: (%s) %s: %s", ros::this_node::getName().c_str(), msg.c_str(), ss.str().c_str());
	}

	/*-----------------*/
	/* action dispatch */
	/*-----------------*/

	/*
	 * Loop through and publish planned actions
	 */
	bool AdaptablePlanDispatcher::dispatchPlan(double missionStartTime, double planStartTime) {

		ROS_INFO("KCL: (%s) Dispatching plan.", ros::this_node::getName().c_str());

		mission_start_time = ros::WallTime::now().toSec();

		ros::Rate loop_rate(10);
		replan_requested = false;
		plan_cancelled = false;

		// initialise machine
		initialise();

		// begin execution
		finished_execution = false;
		state_changed = false;
		bool plan_started = false;

		int test_value = 0;

		while (ros::ok() && !finished_execution) {

			// ROS_INFO("ISR: (%s) Beginning while loop", ros::this_node::getName().c_str());

			// loop while dispatch is paused
			while (ros::ok() && dispatch_paused) {
				ros::spinOnce();
				loop_rate.sleep();
			}

			// cancel plan
			if(plan_cancelled) {
				ROS_INFO("KCL: (%s) Plan cancelled.", ros::this_node::getName().c_str());
				break;
			}

			finished_execution = true;
			state_changed = false;

			// printEsterelPlan();

			printMap(action_dispatched, "action_dispatched");
			printMap(action_completed, "action_completed");
			// ROS_INFO("ISR: (%s) Going inside for loop", ros::this_node::getName().c_str());
			// for nodes check conditions, and dispatch
			for(std::vector<rosplan_dispatch_msgs::EsterelPlanNode>::const_iterator ci = current_plan.nodes.begin(); ci != current_plan.nodes.end(); ci++) {

				rosplan_dispatch_msgs::EsterelPlanNode node = *ci;

				ROS_INFO("ISR: (%s) -----------------------------", ros::this_node::getName().c_str());
				ROS_INFO("ISR: (%s) Node id: %d", ros::this_node::getName().c_str(), node.node_id);
				ROS_INFO("ISR: (%s) Full node name: %s", ros::this_node::getName().c_str(), getFullActionName(node).c_str());
				// std::string node_type;
				// if(node.node_type == node.ACTION_START)
				// 	node_type = "ACTION_START";
				// else if(node.node_type == node.ACTION_END)
				// 	node_type = "ACTION_END";
				// else if(node.node_type == node.PLAN_START)
				// 	node_type = "PLAN_START";
				// ROS_INFO("ISR: (%s) Node type: %s", ros::this_node::getName().c_str(), node_type.c_str());

				// std::vector<int> edges_in = node.edges_in;
				// std::vector<int> edges_out = node.edges_out;
				// printVectorInts(edges_in, "Edges in");
				// printVectorInts(edges_out, "Edges out");

				// if(node.node_type == rosplan_dispatch_msgs::EsterelPlanNode::ACTION_START){
				// 	ROS_INFO("ISR: (%s) Node is action start: %d", ros::this_node::getName().c_str(), node.node_id);
				// }
				// else if(node.node_type == rosplan_dispatch_msgs::EsterelPlanNode::ACTION_END){
				// 	ROS_INFO("ISR: (%s) Node is action end: %d", ros::this_node::getName().c_str(), node.node_id);
				// }

				// activate plan start edges
				if(node.node_type == rosplan_dispatch_msgs::EsterelPlanNode::PLAN_START && !plan_started) {
					// activate new edges
					// ROS_INFO("ISR: (%s) Found PLAN_START", ros::this_node::getName().c_str());
					std::vector<int>::const_iterator ci = node.edges_in.begin();
					ci = node.edges_out.begin();
					for(; ci != node.edges_out.end(); ci++) {
						edge_active[*ci] = true;
					}

					finished_execution = false;
					// state_changed = true;
					plan_started = true;
				}

				// do not check actions for nodes which are not action nodes
				if(node.node_type != rosplan_dispatch_msgs::EsterelPlanNode::ACTION_START && node.node_type != rosplan_dispatch_msgs::EsterelPlanNode::ACTION_END){
					continue;
				}

				// If at least one node is still executing we are not done yet
				if (action_dispatched[node.action.action_id] && !action_completed[node.action.action_id]) {
					finished_execution = false;
				}

				// check action edges
				bool edges_activate_action = true;
				std::vector<int>::iterator eit = node.edges_in.begin();
				for (; eit != node.edges_in.end(); ++eit) {
					if(!edge_active[(*eit)]){
						edges_activate_action = false;
					}
				}
				if(!edges_activate_action) continue;

				// dispatch new action
				if(node.node_type == rosplan_dispatch_msgs::EsterelPlanNode::ACTION_START && !action_dispatched[node.action.action_id]) {
					// ROS_INFO("ISR: (%s) Trying to dispatch start action", ros::this_node::getName().c_str());

					finished_execution = false;

					// query KMS for condition edges
					bool condition_activate_action = false;
					if(edges_activate_action) {
						condition_activate_action = checkStartPreconditions(node.action);
					}

					if(condition_activate_action) {

						// activate action
						// action_dispatched[node.action.action_id] = true;
						action_dispatched.insert(std::make_pair(node.node_id, true));
						// printMap(action_dispatched, "action_dispatched after");
						action_received[node.action.action_id] = false;
						// action_completed[node.action.action_id] = false;
						action_completed.insert(std::make_pair(node.node_id, false));

						std::stringstream full_name_ss;
						full_name_ss << node.action.name;
                        std::vector<diagnostic_msgs::KeyValue, std::allocator<diagnostic_msgs::KeyValue>> action_params = node.action.parameters;

                        for(diagnostic_msgs::KeyValue param: action_params){
							full_name_ss << "#";
                            full_name_ss << param.value;
                        }

						// dispatch action start
						ROS_INFO("KCL: (%s) Dispatching action start [%s]", ros::this_node::getName().c_str(), full_name_ss.str().c_str());

						action_dispatch_publisher.publish(node.action);
                        actions_executing.push_back(node.node_id);
						state_changed = true;

						// deactivate incoming edges
						std::vector<int>::const_iterator ci = node.edges_in.begin();
						for(; ci != node.edges_in.end(); ci++) {
							edge_active[*ci] = false;
						}

						// activate new edges
						ci = node.edges_out.begin();
						for(; ci != node.edges_out.end(); ci++) {
							edge_active[*ci] = true;
						}

						map_node_id.insert(std::make_pair(full_name_ss.str(), node.action.action_id));
						// Waits for the set time in microseconds
						// Wait so the print of rosplan_interface occurs
						// before the print of the state's perturbation
						usleep(10000);

						perturbWorldState();

						// break;
					}
					else{
						ROS_INFO("ISR: (%s) Action is no longer applicable [%i, %s]",
								ros::this_node::getName().c_str(),
								node.action.action_id,
								node.action.name.c_str());
						ROS_INFO("ISR: (%s) Must build a new plan", ros::this_node::getName().c_str());
						state_changed = true;
						break;
						// continue;
					}
				}

				// handle completion of an action
				if(node.node_type == rosplan_dispatch_msgs::EsterelPlanNode::ACTION_END && action_completed[node.action.action_id]) {
					// ROS_INFO("ISR: (%s) Trying to dispatch end action", ros::this_node::getName().c_str());

					// query KMS for condition edges
					bool condition_activate_action = false;
					if(edges_activate_action) {
						condition_activate_action = checkEndPreconditions(node.action);
					}

					if(condition_activate_action) {

						std::stringstream full_name_ss;
						full_name_ss << node.action.name;
						std::vector<diagnostic_msgs::KeyValue, std::allocator<diagnostic_msgs::KeyValue>> action_params = node.action.parameters;

						for(diagnostic_msgs::KeyValue param: action_params){
							full_name_ss << "#";
							full_name_ss << param.value;
						}

						map_node_id.insert(std::make_pair(full_name_ss.str(), node.action.action_id));

						// dispatch action end
						ROS_INFO("KCL: (%s) Dispatching action end [%s]", ros::this_node::getName().c_str(), full_name_ss.str().c_str());

						finished_execution = false;
						state_changed = true;
						actions_executing.push_back(node.node_id);
						action_dispatch_publisher.publish(node.action);
						action_completed.insert(std::make_pair(node.node_id, true));
						// action_completed[node.node_id] = true;
						// printMap(action_completed, "action_completed after");
						// actions_executing.erase(std::remove(actions_executing.begin(), actions_executing.end(), node.action.action_id), actions_executing.end());


						// deactivate incoming edges
						std::vector<int>::const_iterator ci = node.edges_in.begin();
						for(; ci != node.edges_in.end(); ci++) {
							edge_active[*ci] = false;
						}

						// activate new edges
						ci = node.edges_out.begin();
						for(; ci != node.edges_out.end(); ci++) {
							edge_active[*ci] = true;
						}

						// Waits for the set time in microseconds
						// Wait so the print of rosplan_interface occurs
						// before the print of the state's perturbation
						usleep(10000);

						perturbWorldState();

						// break;
					}
					else{
						ROS_INFO("ISR: (%s) Action is no longer applicable [%i, %s]",
								ros::this_node::getName().c_str(),
								node.action.action_id,
								node.action.name.c_str());
						ROS_INFO("ISR: (%s) Must build a new plan", ros::this_node::getName().c_str());
						state_changed = true;
						break;
						// continue;
					}
				}

			} // end loop (action nodes)
			// ROS_INFO("ISR: (%s) Exiting for loop", ros::this_node::getName().c_str());

			ros::spinOnce();
			loop_rate.sleep();

			if(goalAchieved()){
				ROS_INFO("KCL: (%s) Goal is achieved", ros::this_node::getName().c_str());
				finished_execution = true;
			}
			else if(state_changed) {
				ROS_INFO("KCL: (%s) Goal is not achieved", ros::this_node::getName().c_str());
                ROS_INFO("KCL: (%s) Calling the alternatives generator.", ros::this_node::getName().c_str());
                rosplan_dispatch_msgs::ExecAlternatives srv;
                srv.request.actions_executing = actions_executing;
                if(!gen_alternatives_client.call(srv)) {
                    ROS_ERROR("KCL: (%s) could not call the generate alternatives service.", ros::this_node::getName().c_str());
                    return false;
                }
                replan_requested = srv.response.replan_needed;
				removeNextActionFromCompletedAndDispatched(srv.response.next_action);
    			plan_received = false;
		        while (ros::ok() && !plan_received && !replan_requested) {
                    ros::spinOnce();
                    loop_rate.sleep();
                }
                
				ROS_INFO("KCL: (%s) Restarting the dispatch loop.", ros::this_node::getName().c_str());
                // printPlan();
				// initialise();

				// ROS_INFO("ISR: (%s) Finished execution A: %s %d", ros::this_node::getName().c_str(), finished_execution ? "True" : "False", test_value);
            }

			// cancel dispatch on replan
			if(replan_requested) {
				ROS_INFO("KCL: (%s) Replan requested.", ros::this_node::getName().c_str());
				reset();
				return false;
			}
		
			// ROS_INFO("ISR: (%s) Finished execution B: %s %d", ros::this_node::getName().c_str(), finished_execution ? "True" : "False", test_value);
			test_value++;
			// ROS_INFO("ISR: (%s) ---------------------------------", ros::this_node::getName().c_str());
		}

		// ROS_INFO("ISR: (%s) Test value C: %d", ros::this_node::getName().c_str(), test_value);
		ROS_INFO("KCL: (%s) Dispatch complete.", ros::this_node::getName().c_str());

		reset();
		return true;
	}

	void AdaptablePlanDispatcher::initialise() {

		for(std::vector<rosplan_dispatch_msgs::EsterelPlanNode>::const_iterator ci = current_plan.nodes.begin(); ci != current_plan.nodes.end(); ci++) {
			action_dispatched[ci->action.action_id] = false;
			action_received[ci->action.action_id] = false;
			action_completed[ci->action.action_id] = false;
		}

		for(std::vector<rosplan_dispatch_msgs::EsterelPlanEdge>::const_iterator ci = current_plan.edges.begin(); ci != current_plan.edges.end(); ci++) {
			edge_active[ci->edge_id] = false;
		}
	}

	/*------------------*/
	/* general feedback */
	/*------------------*/

	/**
	 * listen to and process actionFeedback topic.
	 */
	void AdaptablePlanDispatcher::feedbackCallback(const rosplan_dispatch_msgs::ActionFeedback::ConstPtr& msg) {

		ROS_INFO("KCL: (%s) Feedback received [%i, %s]", ros::this_node::getName().c_str(), msg->action_id, msg->status.c_str());

		// action enabled
		if(!action_received[msg->action_id] && (0 == msg->status.compare("action enabled"))) {
			action_received[msg->action_id] = true;
		}

		// action completed (successfuly)
		if(!action_completed[msg->action_id] && 0 == msg->status.compare("action achieved")) {

			// check action is part of current plan
			if(!action_received[msg->action_id]) {
				ROS_INFO("KCL: (%s) Action not yet dispatched, ignoring feedback", ros::this_node::getName().c_str());
			}
			action_completed[msg->action_id] = true;
		}

		// action completed (failed)
		if(!action_completed[msg->action_id] && 0 == msg->status.compare("action failed")) {
			replan_requested = true;
			action_completed[msg->action_id] = true;
		}
	}

	/*-------------------*/
	/* Produce DOT graph */
	/*-------------------*/

	void AdaptablePlanDispatcher::printPlan() {

		// output stream
		std::stringstream dest;

		dest << "digraph plan" << " {" << std::endl;

		// nodes
		for(std::vector<rosplan_dispatch_msgs::EsterelPlanNode>::iterator nit = current_plan.nodes.begin(); nit!=current_plan.nodes.end(); nit++) {

			std::stringstream params;
			// do not print parameters for start node
			if(nit->node_type != rosplan_dispatch_msgs::EsterelPlanNode::PLAN_START) {
				// to print action parameters in graph, get parameters from action
				for(auto pit = nit->action.parameters.begin(); pit != nit->action.parameters.end(); pit++) {
					params << pit-> value << ",";
				}
				// replace last character "," with a ")"
				params.seekp(-1, params.cur); params << ')';
				dest <<  nit->node_id << "[ label=\"" << nit->node_id << ". " << nit->name << "\n(" << params.str();
			}
			else {

				dest <<  nit->node_id << "[ label=\"" << nit->node_id << ". " << nit->name;
			}

			switch(nit->node_type) {
			case rosplan_dispatch_msgs::EsterelPlanNode::ACTION_START:
				if(action_received[nit->action.action_id]) {
					dest << "\",style=filled,fillcolor=darkolivegreen,fontcolor=white];" << std::endl;
				} else if(action_dispatched[nit->action.action_id]) {
					dest << "\",style=filled,fillcolor=darkgoldenrod2];" << std::endl;
				} else {
					dest << "\"];" << std::endl;
				}
				break;
			case rosplan_dispatch_msgs::EsterelPlanNode::ACTION_END:
				if(action_completed[nit->action.action_id]) {
					dest << "\",style=filled,fillcolor=darkolivegreen,fontcolor=white];" << std::endl;
				} else if(action_dispatched[nit->action.action_id]) {
					dest << "\",style=filled,fillcolor=darkgoldenrod2];" << std::endl;
				} else {
					dest << "\"];" << std::endl;
				}
				break;
			case rosplan_dispatch_msgs::EsterelPlanNode::PLAN_START:
				dest << "\",style=filled,fillcolor=black,fontcolor=white];" << std::endl;
				break;
			default:
				dest << "\"];" << std::endl;
				break;
			}
		}

		// edges
		for(std::vector<rosplan_dispatch_msgs::EsterelPlanEdge>::iterator eit = current_plan.edges.begin(); eit!=current_plan.edges.end(); eit++) {
			for(int j=0; j<eit->sink_ids.size(); j++) {
			for(int i=0; i<eit->source_ids.size(); i++) {

				dest << "\"" << eit->source_ids[i] << "\"" << " -> \"" << eit->sink_ids[j] << "\"";
				if(eit->duration_upper_bound == std::numeric_limits<double>::max()) {
					dest << " [ label=\"" << eit->edge_id << "[" << eit->duration_lower_bound << ", " << "inf]\"";
				} else {
					dest << " [ label=\"" << eit->edge_id << "[" << eit->duration_lower_bound << ", " << eit->duration_upper_bound << "]\"";
				}

				// decide edge color
				std::string edge_color = "black";

				if(display_edge_type_) {

					// green if conditional edge, red if start to end, blue if interference edge
					if(eit->edge_type == rosplan_dispatch_msgs::EsterelPlanEdge::CONDITION_EDGE){
					edge_color = "green";
					}
					else if(eit->edge_type == rosplan_dispatch_msgs::EsterelPlanEdge::INTERFERENCE_EDGE){
							edge_color = "blue";
					}
					else if(eit->edge_type == rosplan_dispatch_msgs::EsterelPlanEdge::START_END_ACTION_EDGE){
							edge_color = "red";
					}
				}
				else {

					if(edge_active[eit->edge_id]) {
							edge_color = "red";
					}
					else {
							edge_color = "black";
					}
				}

				dest << " , penwidth=2, color=\"" << edge_color << "\"]" << std::endl;

			}};
		}

		dest << "}" << std::endl;

		// publish on topic
		std_msgs::String msg;
		msg.data = dest.str();
		plan_graph_publisher.publish(msg);
	}
} // close namespace

	/*-------------*/
	/* Main method */
	/*-------------*/

	int main(int argc, char **argv) {

		ros::init(argc,argv,"rosplan_esterel_plan_dispatcher");
		ros::NodeHandle nh("~");

		KCL_rosplan::AdaptablePlanDispatcher epd(nh);

		// subscribe to planner output
		std::string planTopic = "complete_plan";
		nh.getParam("plan_topic", planTopic);
		ros::Subscriber plan_sub = nh.subscribe(planTopic, 1, &KCL_rosplan::AdaptablePlanDispatcher::planCallback, &epd);

		std::string feedbackTopic = "action_feedback";
		nh.getParam("action_feedback_topic", feedbackTopic);
		ros::Subscriber feedback_sub = nh.subscribe(feedbackTopic, 1000, &KCL_rosplan::AdaptablePlanDispatcher::feedbackCallback, &epd);

		ROS_INFO("KCL: (%s) Ready to receive", ros::this_node::getName().c_str());
		ros::spin();

		return 0;
	}
