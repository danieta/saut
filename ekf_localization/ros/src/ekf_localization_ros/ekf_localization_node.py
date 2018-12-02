#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ROS python api with lots of handy ROS functions
import rospy

# to be able to get the current frames and positions
import tf

# to be able to subcribe to laser scanner data
from sensor_msgs.msg import LaserScan

# to be able to publish Twist data (and move the robot)
from geometry_msgs.msg import Twist

# to be able to get the map
from nav_msgs.msg import OccupancyGrid

# to be able to do matrix multiplications
import numpy as np


class ekf_localization(object):
    '''
    Exposes a behavior for the pioneer robot so that moves forward until
    it has an obstacle at 1.0 m then stops rotates for some time to the
    right and resumes motion.
    '''
    def __init__(self):
        '''
        Class constructor: will get executed at the moment
        of object creation
        '''
        # register node in ROS network
        rospy.init_node('ekf_localization_node', anonymous=False)

        # print message in terminal
        rospy.loginfo('ekf localization started !')
        # subscribe to pioneer laser scanner topic
        if rospy.has_param('laser_topic'):
            # retrieves the name of the LaserScan topic from the parameter server if it exists
            rospy.Subscriber(rospy.get_param('laser_topic'), LaserScan, self.laser_callback)
        else:
            rospy.Subscriber("/scan", LaserScan, self.laser_callback)
        
        # setup publisher to later on move the pioneer base
        # self.pub_cmd_vel = rospy.Publisher(rospy.get_param('robot_name')+'/cmd_vel', Twist, queue_size=1)
        # define member variable and initialize with a big value
        # it will store the distance from the robot to the walls
        self.distance = 10.0
        # create a tf listener and broadcaster instance to update tf and get positions
        self.listener = tf.TransformListener()
        self.br = tf.TransformBroadcaster()

        # starting point for the odometry
        now = rospy.Time.now()
        self.listener.waitForTransform("base_link", "odom", now, rospy.Duration(10.0))
        try:
            
            (trans,quat) = self.listener.lookupTransform("base_link", "odom", now)
        except:
            rospy.loginfo("No odom!!!")
            trans = np.zeros((3,1))
            quat = np.array([0, 0, 0, 1.0])

        rot = tf.transformations.euler_from_quaternion(quat)

        print(trans)

        # defines the distance threshold below which the robot should relocalize
        print("check")
        print(rospy.has_param('distance_threshold'))
        if rospy.has_param('distance_threshold'):
            self.distance_threshold = rospy.get_param('distance_threshold')
        else:
            self.distance_threshold = 1.0


        # defines the angle threshold below which the robot should relocalize
        if rospy.has_param('angle_threshold'):
            self.angle_threshold = rospy.get_param('angle_threshold')
        else:
            self.angle_threshold = 0.34906585

        # iniitialize belief of where the robot is. transpose to get a column vector
        self.current_belief = np.array(rospy.get_param('belief', [0.0, 0.0, 0.0])).T
        self.trans = np.array([self.current_belief[0], self.current_belief[1], 0])
        self.rot = np.array([0, 0, self.current_belief[2]])

         # NEED TO TWEAK THE DIAGONAL VALUES. 
        self.sigma = np.reshape(np.array(rospy.get_param('sigma', 
                            [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0])), (3, 3))

        # NEED TO TWEAK THE DIAGONAL VALUES. See presentation 3, slide 10
        self.R = np.array([[1,0,0], 
                           [0,1,0],
                           [0,0,1]])

        # NEED TO TWEAK THE DIAGONAL VALUES
        self.Q = np.array([[1,0], 
                           [0,1]])

        trans = self.trans - trans
        quat = tf.transformations.quaternion_from_euler(0.0, 0.0, self.current_belief[2]-rot[2])

        # publish the starting transformation between map and odom frame
        self.br.sendTransform(trans,
                         quat,
                         rospy.Time.now(),
                         "odom",
                         "map")

        
    '''
    def rotate_right(self):
        #Rotate the robot by a certain angle

        # create empty message of Twist type (check http://docs.ros.org/api/geometry_msgs/html/msg/Twist.html)
        twist_msg = Twist()
        # linear speed
        twist_msg.linear.x = 0.0
        twist_msg.linear.y = 0.0
        twist_msg.linear.z = 0.0
        # angular speed
        twist_msg.angular.x = 0.0
        twist_msg.angular.y = 0.0
        twist_msg.angular.z = -0.3

        # publish Twist message to /robot_0/cmd_vel to move the robot
        self.pub_cmd_vel.publish(twist_msg)


    def move_forward(self):

        #Move the robot forward some distance

        # create empty message of Twist type (check http://docs.ros.org/api/geometry_msgs/html/msg/Twist.html)
        twist_msg = Twist()
        # linear speed
        twist_msg.linear.x = 0.5
        twist_msg.linear.y = 0.0
        twist_msg.linear.z = 0.0
        # angular speed
        twist_msg.angular.x = 0.0
        twist_msg.angular.y = 0.0
        twist_msg.angular.z = 0.0

        # publish Twist message to /robot_0/cmd_vel to move the robot
        self.pub_cmd_vel.publish(twist_msg)
    '''

    def laser_callback(self, msg):

        #This function gets executed everytime a laser scanner msg is received on the
        #topic: /robot_0/base_scan_1

        # ============= YOUR CODE GOES HERE! =====
        # hint: msg contains the laser scanner msg
        # hint: check http://docs.ros.org/api/sensor_msgs/html/msg/LaserScan.html
        middle = len(msg.ranges)/2
        delta_angle = 0.3
        delta_index = int(delta_angle/msg.angle_increment)
        useful_ranges = msg.ranges[middle - delta_index : middle + delta_index]

        self.distance = min(useful_ranges)


        # ============= YOUR CODE ENDS HERE! =====



    #H: measurement model (maps the state we're in to the measurement we expect to see)
    #G: motion model
    #Q: model of sensor's error (covariance matrix)
    #K: Kalman gain


    # TO DO: find H and G !!!!!

    '''
    def h(x,y,theta,x_n,y_n,theta_n):
        distance = np.sqrt( (x_n - x)² + (y_n - y)² )
        angle = np.arctan( (y_n - y) / (x_n - x) ) - theta

        return (distance, angle)
    '''

    def kalman_filter(self):
        
        now = rospy.Time.now()
        # get the odometry

        self.listener.waitForTransform("base_link", "map", now, rospy.Duration(10.0))
        try:
            
            (current_trans,current_quat) = self.listener.lookupTransform("base_link", "map", now)
        except:
            rospy.loginfo("No odom!!!")
            current_trans = np.zeros((3,1))
            current_quat = np.array([0, 0, 0, 1.0])

        current_rot = tf.transformations.euler_from_quaternion(current_quat)

        odometry_trans = current_trans - self.trans
        odometry_rot = current_rot - self.rot

        rospy.loginfo(str(odometry_trans))
        rospy.loginfo(str(odometry_rot))

        # The distance in x and y moved, and the rotation about z
        delta_odom = np.array([odometry_trans[0],  odometry_trans[1],  odometry_rot[2]]).T

        #dont do anything if the distance traveled and angle rotated is too small
        if(np.sqrt(delta_odom[0]**2 + delta_odom[1]**2)<self.distance_threshold and delta_odom[2] < self.angle_threshold):
            return


        # delta_D_k*cos(theta_k) is the 0th element of the translation given by odometry. delta_D_k*sin(theta_k) is the 1st. 
        G = np.matrix([ [1, 0, -odometry_trans[1]], 
                        [0, 1, odometry_trans[0]], 
                        [0, 0, 1] ])

        
        

        #PREDICT
        mu_predicted = self.current_belief + delta_odom
        sigma_predicted = np.matmul( np.matmul(G, self.sigma), G.transpose ) + self.R #NEED TO DEFINE R, COVARIANCE OF THE STATE TRANSITION NOISE

        '''
        # UPDATE/CORRECT
        for i in range(NUMBER_OF_OBSERVATIONS): #NEED TO DEFINE NUMBER_OF_OBSERVATIONS. This should be equal to the number of rays we make
            #NEED TO DEFINE theta_n and d_n. This should be the constant angle between each ray
            H[i] = np.matrix([-np.cos(current_rot[2] + i*theta_n), -np.sin(current_rot[2] + i*theta_n), 0] 
                             [(np.sin(current_rot[2] + i*theta_n)) / d_n, -np.cos(current_rot[2] + i*theta_n) / d_n, -1])





        sigmaH = np.matmul( sigma, H.transpose )    # step 3: Kalman gain calculation (I've broken the calculation in two steps)
        K = np.matmul( sigmaH, np.linalg.inv( np.matmul( H, sigmaH ) + Q ) )
        '''     
        #update
        self.current_belief = mu_predicted      #+ np.matmul( K, z - exp_meas(predicted_state) )
        self.trans = np.array([self.current_belief[0], self.current_belief[1], 0])
        self.rot = np.array([0, 0, self.current_belief[2]]) 
        self.sigma = sigma_predicted    #np.matmul( I - np.matmul( K, H ), new_sigma )

        rospy.set_param('sigma', self.sigma.flatten.tolist)
        






    # returns the measurement we expect to see when we're in a given state
    # here we have to do the ray tracing
    def exp_measurement (state):
        
        return z_expected



    def run_behavior(self):
        rospy.loginfo('Working')
        while not rospy.is_shutdown():
            rospy.loginfo('Working')
            self.kalman_filter()

            # sleep for a small amount of time
            rospy.sleep(0.1)



#def main():
#    print('Hello')
#    # create object of the class ekf_localization (constructor will get executed!)
#    my_object = ekf_localization()
#    # call run_behavior method of class EKF_localization
#    my_object.run_behavior()

if __name__ == '__main__':
     # create object of the class ekf_localization (constructor will get executed!)
     my_object = ekf_localization()
     # call run_behavior method of class EKF_localization
     my_object.run_behavior()
