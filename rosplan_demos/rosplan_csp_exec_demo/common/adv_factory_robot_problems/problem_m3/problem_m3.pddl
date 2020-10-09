(define (problem task)
(:domain factory_robot)

(:objects
    m1 m2 m3 - machine
)

(:init
    (robot_at m1)
    (machine_is_working m1)
    (machine_is_working m2)
    (machine_is_working m3)
)

(:goal (and
            (machine_is_maintained m1)
            (machine_is_maintained m2)
            (machine_is_maintained m3)
       )
)

)