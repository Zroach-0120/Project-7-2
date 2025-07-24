from CollideObjectBase import SphereCollideObject
from CollideObjectBase import SphereCollideObject
from panda3d.core import Loader, NodePath, Vec3, Filename, CollisionSphere, ClockObject
from direct.task.Task import TaskManager, Task
from typing import Callable
from SpaceJamClasses import Drone, Missile
import math, random, re
from direct.interval.LerpInterval import LerpFunc
from direct.particles.ParticleEffect import ParticleEffect
from panda3d.core import CollisionHandlerEvent


class Spaceship(SphereCollideObject):
    def __init__(self, loader: Loader, taskMgr, accept: Callable[[str, Callable], None], 
                 modelPath: str, parentNode: NodePath, nodeName: str, texPath: str, 
                 posVec: Vec3, scaleVec: float, camera, traverser, handler):

        super().__init__(loader, modelPath, parentNode, nodeName, Vec3(0, 0, 0), 0.01)
        
        # Setup basic model
        self.modelNode.setPos(posVec)
        self.modelNode.setScale(scaleVec)
        self.modelNode.setName(nodeName)
        self.modelNode.setHpr(0, -90, 0)
        self.collisionNode.show()

        tex = loader.loadTexture(texPath)
        self.modelNode.setTexture(tex, 1)

        # Init handlers and references
        self.loader = loader
        self.render = parentNode
        self.accept = accept
        self.traverser = traverser
        self.handler = CollisionHandlerEvent()
        self.handler.addInPattern('into')
        self.accept('into', self.HandleInto)

        self.taskMgr = taskMgr
        self.camera = camera
       

        # Movement and physics
        self.velocity = Vec3(0, 0, 0)
        self.base_acceleration = 50
        self.acceleration_magnitude = self.base_acceleration
        self.base_speed = 500
        self.current_speed = self.base_speed
        self.max_speed = 3000
        self.damping = 0.99

        # Boost
        self.boost_multiplier = 10
        self.boost_duration = 10
        self.boost_cooldown = 5
        self.can_boost = True
        self.boost_status_callback = None

        # Missile firing
        self.reloadTime = 0.25
        self.missileDistance = 4000
        self.missileBay = 1
        self.taskMgr.add(self.CheckIntervals, 'checkMissiles', 34)

        # Particles
        self.SetParticles()
        self.cntExplode = 0
        self.explodeIntervals = {}

        # Camera
        self.zoom_factor = 5
        self.cameraZoomSpeed = 10

        # Clock
        self.globalClock = ClockObject.getGlobalClock()

        # Task for movement
        self.taskMgr.add(self.UpdateMovement, "update-movement")

    


    def SetParticles(self):
        self.explodeEffect = ParticleEffect()
        self.explodeEffect.loadConfig("./Assets/Part-Efx/basic_xpld_efx.ptf")
        self.explodeEffect.setScale(20)
        self.explodeNode = self.render.attachNewNode('ExplosionEffects')

    def Boost(self):
        if not self.can_boost:
            print("Boost is on cooldown!")
            if self.boost_status_callback:
                self.boost_status_callback("COOLDOWN")
            return

        self.can_boost = False
        self.acceleration_magnitude = self.base_acceleration * self.boost_multiplier
        print("Boost activated! Acceleration multiplied.")
        if self.boost_status_callback:
            self.boost_status_callback("ACTIVE")

        self.taskMgr.doMethodLater(self.boost_duration, self.EndBoost, 'end-boost')

    def EndBoost(self, task):
        self.acceleration_magnitude = self.base_acceleration
        print("Boost ended. Acceleration back to normal.")
        if self.boost_status_callback:
            self.boost_status_callback("COOLDOWN")
        self.taskMgr.doMethodLater(self.boost_cooldown, self.ResetBoost, 'reset-boost')
        return Task.done

    def ResetBoost(self, task):
        self.can_boost = True
        print("Boost ready again.")
        if self.boost_status_callback:
            self.boost_status_callback("READY")
        return Task.done

    def move_forward(self, keyDown):
        if keyDown:
            if not self.taskMgr.hasTaskNamed('apply-thrust'):
                self.taskMgr.add(self.ApplyThrust, 'apply-thrust')
        else:
            if self.taskMgr.hasTaskNamed('apply-thrust'):
                self.taskMgr.remove('apply-thrust')

    def ApplyThrust(self, task):
        dt = self.globalClock.getDt()
        forward_vec = self.modelNode.getQuat().getForward()
        self.velocity += forward_vec * self.acceleration_magnitude * dt

        if self.velocity.length() > self.max_speed:
            self.velocity.normalize()
            self.velocity *= self.max_speed

        return Task.cont

    def UpdateMovement(self, task):
        dt = self.globalClock.getDt()
        self.velocity *= self.damping
        new_pos = self.modelNode.getPos() + self.velocity * dt
        self.modelNode.setPos(new_pos)
        return Task.cont

    # ... [rest of your methods unchanged] ...


    def CheckIntervals(self, task):
        for i in list(Missile.Intervals.keys()):
            if not Missile.Intervals[i].isPlaying():
                Missile.cNodes[i].detachNode()
                Missile.fireModels[i].detachNode()
                del Missile.Intervals[i]
                del Missile.fireModels[i]
                del Missile.cNodes[i]
                del Missile.collisionSolids[i]
                print(i + ' has ended.')
        return Task.cont

    def Fire(self):
        if self.missileBay:
            travRate = self.missileDistance
            aim = self.render.getRelativeVector(self.modelNode, Vec3.forward())
            aim.normalize()
            fireSolution = aim * travRate
            inFront = aim * 150
            travVec = fireSolution + self.modelNode.getPos()

            tag = 'Missile' + str(Missile.missileCount)
            posVec = self.modelNode.getPos() + inFront
            currentMissile = Missile(self.loader, "./Assets/Phaser/phaser.egg", self.render, tag, posVec, 4.0)
            self.traverser.addCollider(currentMissile.collisionNode, self.handler)
            Missile.Intervals[tag] = currentMissile.modelNode.posInterval(2.0, travVec, startPos=posVec, fluid=1)
            Missile.Intervals[tag].start()
        else:
            if not self.taskMgr.hasTaskNamed('reload'):
                print('Reloading...')
                self.taskMgr.doMethodLater(0, self.Reload, 'reload')
                return Task.cont

    def Reload(self, task):
        if task.time > self.reloadTime:
            self.missileBay = 1
            print("Reload complete")
            return Task.done
        print("Reloading...")
        return Task.cont

    def HandleInto(self, entry):
        fromNode = entry.getFromNodePath().getName()
        intoNode = entry.getIntoNodePath().getName()
        intoPosition = Vec3(entry.getSurfacePoint(self.render))

        shooter = fromNode.split('_')[0]
        victim = intoNode.split('_')[0]
        stripped = re.sub(r'[0-9]', '', victim)

        if stripped in ("Drone", "Planet", "Space Station"):
            print(f"{victim} hit at {intoPosition}")
            self.DestroyObject(victim, intoPosition)

        if shooter in Missile.Intervals:
            Missile.Intervals[shooter].finish()
        else:
            print(f"Warning: No interval found for '{shooter}'")

    def DestroyObject(self, hitID, hitPosition):
        nodeID = self.render.find(hitID)
        nodeID.detachNode()
        self.explodeNode.setPos(hitPosition)
        self.Explode()

    def Explode(self):
        self.cntExplode += 1
        tag = 'particles-' + str(self.cntExplode)
        self.explodeIntervals[tag] = LerpFunc(self.ExplodeLight, duration=4.0)
        self.explodeIntervals[tag].start()

    def ExplodeLight(self, t):
        if t == 1.0 and self.explodeEffect:
            self.explodeEffect.disable()
        elif t == 0:
            self.explodeEffect.start(self.explodeNode)

    def turn_left(self, keyDown):
        if keyDown:
            self.taskMgr.add(self.ApplyTurnLeft, 'turn-left')
        else:
            self.taskMgr.remove('turn-left')

    def ApplyTurnLeft(self, task):
        self.modelNode.setH(self.modelNode.getH() + 1.5)
        return Task.cont

    def turn_right(self, keyDown):
        if keyDown:
            self.taskMgr.add(self.ApplyTurnRight, 'turn-right')
        else:
            self.taskMgr.remove('turn-right')

    def ApplyTurnRight(self, task):
        self.modelNode.setH(self.modelNode.getH() - 1.5)
        return Task.cont

    def turn_up(self, keyDown):
        if keyDown:
            self.taskMgr.add(self.ApplyTurnUp, 'turn-up')
        else:
            self.taskMgr.remove('turn-up')

    def ApplyTurnUp(self, task):
        self.modelNode.setP(self.modelNode.getP() - 1.5)
        return Task.cont

    def turn_down(self, keyDown):
        if keyDown:
            self.taskMgr.add(self.ApplyTurnDown, 'turn-down')
        else:
            self.taskMgr.remove('turn-down')

    def ApplyTurnDown(self, task):
        self.modelNode.setP(self.modelNode.getP() + 1.5)
        return Task.cont


    

    def zoom_in(self, keyDown):
        if keyDown:
            self.taskMgr.add(self.ApplyZoomIn, 'zoom-in')
        else:
            self.taskMgr.remove('zoom-in')

    def ApplyZoomIn(self, task):
        self.camera.setPos(self.camera.getPos() + Vec3(0, self.cameraZoomSpeed, 0))
        return Task.cont

    def zoom_out(self, keyDown):
        if keyDown:
            self.taskMgr.add(self.ApplyZoomOut, 'zoom-out')
        else:
            self.taskMgr.remove('zoom-out')

    def ApplyZoomOut(self, task):
        self.camera.setPos(self.camera.getPos() + Vec3(0, -self.cameraZoomSpeed, 0))
        return Task.cont

    def attach_drone_rings(self, numDronesPerRing=12, radius=20):
        ringParent = self.modelNode.attachNewNode("AllDroneRings")
        angleStep = 2 * math.pi / numDronesPerRing

        for axis in ['x', 'y', 'z']:
            for i in range(numDronesPerRing):
                angle = i * angleStep
                pos = Vec3()
                if axis == 'x':
                    pos.y = math.cos(angle) * radius
                    pos.z = math.sin(angle) * radius
                elif axis == 'y':
                    pos.x = math.cos(angle) * radius
                    pos.z = math.sin(angle) * radius
                elif axis == 'z':
                    pos.x = math.cos(angle) * radius
                    pos.y = math.sin(angle) * radius

                Drone(
                    self.loader,
                    "./Assets/DroneDefender/DroneDefender.obj",
                    ringParent,
                    f"Drone-{axis}-{i}",
                    "./Assets/DroneDefender/octotoad1_auv.png",
                    pos,
                    .5
                )

    def set_boost_callback(self, callback):
        self.boost_status_callback = callback
