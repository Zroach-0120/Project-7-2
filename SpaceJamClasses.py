from panda3d.core import NodePath, Vec3, CollisionNode, CollisionSphere, CollisionHandlerQueue, CollisionRay, Filename
import random, math
from direct.task import Task
from CollideObjectBase import *
from direct.task.Task import TaskManager
import DefensePaths as defensePaths
class Universe(InverseSphereCollideObject):
    def __init__(self, loader, modelPath, parentNode, nodeName, texPath, posVec, scaleVec):
        # Use a much larger radius for the universe boundary
        # The 0.9 radius was too small for your universe scale
        super().__init__(loader, modelPath, parentNode, nodeName, Vec3(0,0,0), 0.9)
        
        self.modelNode.reparentTo(parentNode)
        self.modelNode.setPos(posVec)
        self.modelNode.setScale(scaleVec)
        self.modelNode.setName(nodeName)
        
        tex = loader.loadTexture(texPath)
        self.modelNode.setTexture(tex, 1)


class Planet(SphereCollideObject):
    def __init__(self, loader, modelPath, parentNode, nodeName, texPath, posVec, scaleVec):
        super().__init__(loader, modelPath, parentNode, nodeName, Vec3(0, 0, 0), 1.5)
        
        self.modelNode.setPos(posVec)
        self.modelNode.setScale(scaleVec)
        
        tex = loader.loadTexture(texPath)
        self.modelNode.setTexture(tex, 1)
        
        self.collisionNode.node().addSolid(CollisionSphere(0, 0, 0, 5))
        self.collisionNode.show()


class Drone(CollideableObject):
    droneCount = 0
    droneInstances = []
    dronePool = []

    def __init__(self, loader, modelPath, parentNode, nodeName, texPath, posVec, scaleVec):
        super().__init__(loader, modelPath, parentNode, nodeName)

        self.modelNode.reparentTo(parentNode)
        self.modelNode.setPos(posVec)
        self.modelNode.setScale(scaleVec)
        self.modelNode.setName(nodeName)

        tex = loader.loadTexture(texPath)
        self.modelNode.setTexture(tex, 1)

        # Ensure scaleVec is Vec3
        if not isinstance(scaleVec, Vec3):
            scaleVec = Vec3(scaleVec, scaleVec, scaleVec)

        radius = scaleVec.getX() * 0.5
        self.collisionNode.node().addSolid(CollisionSphere(0, 0, 0, radius))
        self.collisionNode.show()

        

        Drone.droneCount += 1
        Drone.droneInstances.append(self)

    def explode(self):
        # Start explosion at drone's position
        self.explodeNode.setPos(self.modelNode.getPos(self.modelNode.getParent()))
        self.explodeEffect.start(self.explodeNode)

        if self in Drone.droneInstances:
            Drone.droneInstances.remove(self)

        self.modelNode.removeNode()

    @staticmethod
    def return_to_pool(drone):
        """Returns the drone to the pool when it is destroyed."""
        if drone in Drone.droneInstances:
            Drone.droneInstances.remove(drone)
        Drone.dronePool.append(drone.modelNode)
        drone.modelNode.removeNode()

class SpaceStation(CapsuleCollideableObject):
    def __init__(self, loader, modelPath, parentNode, nodeName, texPath, posVec, scaleVec):
        super().__init__(loader, modelPath, parentNode, nodeName, 1, -1, 5, 1, -1, -5, 1.5)
        
        self.modelNode.setPos(posVec)
        self.modelNode.setScale(scaleVec)
        self.modelNode.setName(nodeName)

        tex = loader.loadTexture(texPath)
        self.modelNode.setTexture(tex, 1)
    

class Missile(SphereCollideObject):
     fireModels = {}
     cNodes = {}
     collisionSolids = {}
     Intervals = {}
     missileCount = 0

     def __init__(self, loader: Loader, modelPath: str, parentNode: NodePath, nodeName: str, posVec: Vec3, scaleVec: float = 1.0):
         super(Missile, self).__init__(loader, modelPath, parentNode, nodeName, Vec3(0,0,0), 3.0)
         self.modelNode.setScale(scaleVec)
         self.modelNode.setPos(posVec)
         Missile.missileCount += 1
         Missile.fireModels[nodeName] = self.modelNode
         Missile.cNodes[nodeName] = self.collisionNode
         Missile.collisionSolids[nodeName] = self.collisionNode.node().getSolid(0)
         Missile.cNodes[nodeName].show()
         print("Fire rocket #" + str(Missile.missileCount))


class Orbiter(CapsuleCollideableObject):
    # Class variables must be declared before they're used.
    numOrbits = 0
    velocity = 0.005
    cloudTimer = 240

    def __init__(self, loader: Loader, taskMgr: TaskManager, modelPath: str, parentNode: NodePath, nodeName: str, 
                 scaleVec: Vec3, texPath: str, centralObject: PlacedObject, orbitRadius: float, 
                 orbitType: str, staringAt: Vec3):
        # Initialize the base class with a default collision center and radius.
        super().__init__(loader, modelPath, parentNode, nodeName, 1, -1, 5, 1, -1, -5, 1.5)

        
        self.taskMgr = taskMgr
        self.orbitType = orbitType

        self.modelNode.setScale(scaleVec)
        tex = loader.loadTexture(texPath)
        self.modelNode.setTexture(tex, 1)
        
        self.orbitObject = centralObject
        self.orbitRadius = orbitRadius
        self.staringAt = staringAt

        # Increment the class variable and store it in the instance (if needed).
        Orbiter.numOrbits += 1
        self.numOrbits = Orbiter.numOrbits

        self.cloudClock = 0
        self.taskFlag = "Traveler-" + str(self.numOrbits)
        
        # Add the orbit task.
        self.taskMgr.add(self.Orbit, self.taskFlag)

    def Orbit(self, task):
        if self.orbitType == "MLB":
             #Calculate the new position using the MLB orbit function.
            positionVec = defensePaths.BaseballSeams(task.time * Orbiter.velocity, self.numOrbits, 2.0, 1.0)
            newPos = positionVec * self.orbitRadius + self.orbitObject.modelNode.getPos()
            self.modelNode.setPos(newPos)
        elif self.orbitType == "Cloud":
            if self.cloudClock < Orbiter.cloudTimer:
                self.cloudClock += 1
            else:
                self.cloudClock = 0
                positionVec = defensePaths.Cloud()
                newPos = positionVec * self.orbitRadius + self.orbitObject.modelNode.getPos()
                self.modelNode.setPos(newPos)
        
        self.modelNode.lookAt(self.staringAt.modelNode)
        return task.cont
      