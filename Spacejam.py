from direct.showbase.ShowBase import ShowBase
import math, sys, random
import DefensePaths as defensePaths
import SpaceJamClasses as SpaceJamClasses
from panda3d.core import Vec3, Vec4
from Player import Spaceship
from SpaceJamClasses import Drone
from panda3d.core import CollisionTraverser, CollisionHandlerPusher, CollisionHandlerEvent, TransparencyAttrib
from direct.gui.OnscreenImage import OnscreenImage
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode


class MyApp(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        self.cTrav = CollisionTraverser()
        self.pusher = CollisionHandlerPusher()
        self.collisionHandler = CollisionHandlerEvent()
        self.rootAssetFolder = "./Assets"

        self.SetupScene()
        self.SetupCollisions()
        self.cTrav.showCollisions(self.render)
        self.SetKeyBindings()

        self.enableParticles()
        self.missilesLeft = 10
        self.boostLeft = 100.0
        self.Hero.set_boost_callback(self.updateBoostDisplay)

        self.missilesText = OnscreenText(
            text=f"Missiles: {self.missilesLeft}",
            pos=(-1.3, 0.9), scale=0.07, fg=Vec4(1, 1, 1, 1),
            align=TextNode.ALeft, mayChange=True
        )

        self.boostText = OnscreenText(
            text=f"Boost: {int(self.boostLeft)}%",
            pos=(-1.3, 0.8), scale=0.07, fg=Vec4(1, 1, 1, 1),
            align=TextNode.ALeft, mayChange=True
        )

    def SetupScene(self):
        self.Universe = SpaceJamClasses.Universe(
            self.loader, "./Assets/Universe/Universe.obj", self.render,
            'Universe', "Assets/Universe/Universe2.jpg", (0, 0, 0), 18008
        )

        self.Planet1 = SpaceJamClasses.Planet(
            self.loader, "./Assets/Planets/protoPlanet.x", self.render, 'Planet1',
            "./Assets/Planets/WaterPlanet2.png", (0, 0, 0), 250
        )
        self.Planet2 = SpaceJamClasses.Planet(
            self.loader, "./Assets/Planets/protoPlanet.x", self.render, 'Planet2',
            "./Assets/Planets/eris.jpg", (0, 6000, 0), 300
        )
        self.Planet3 = SpaceJamClasses.Planet(
            self.loader, "./Assets/Planets/protoPlanet.x", self.render, 'Planet3',
            "./Assets/Planets/cheeseplanet.png", (500, -5000, 200), 500
        )
        self.Planet4 = SpaceJamClasses.Planet(
            self.loader, "./Assets/Planets/protoPlanet.x", self.render, 'Planet4',
            "./Assets/Planets/earth.jpg", (300, 6000, 500), 150
        )
        self.Planet5 = SpaceJamClasses.Planet(
            self.loader, "./Assets/Planets/protoPlanet.x", self.render, 'Planet5',
            "./Assets/Planets/redmoon.png", (700, -2000, 100), 500
        )
        self.Planet6 = SpaceJamClasses.Planet(
            self.loader, "./Assets/Planets/protoPlanet.x", self.render, 'Planet6',
            "./Assets/Planets/venus.jpg", (0, -980, -1480), 700
        )

        self.SpaceStation1 = SpaceJamClasses.SpaceStation(
            self.loader, "./Assets/SpaceStation/spaceStation.x", self.render, 'SpaceStation1',
            "./Assets/SpaceStation/SpaceStation1_Dif2.png", (1500, 1800, -100), 40
        )

        self.Hero = Spaceship(
            self.loader, self.taskMgr, self.accept, "Assets/Spaceships/spacejet.3ds",
            self.render, 'Hero', "Assets/Spaceships/spacejet_C.png",
            Vec3(900, 1200, -58), 2, self.camera, self.cTrav, self.collisionHandler
        )
        self.Hero.attach_drone_rings()
        self.taskMgr.add(self.UpdateCamera, "UpdateCamera")

        self.Sentinal1 = SpaceJamClasses.Orbiter(
            self.loader, self.taskMgr, self.rootAssetFolder + "/DroneDefender/DroneDefender.obj",
            self.render, "Drone", 6.0, self.rootAssetFolder + "/DroneDefender/octotoad1_auv.png",
            self.Planet5, 900, "MLB", self.Hero
        )
        self.Sentinal2 = SpaceJamClasses.Orbiter(
            self.loader, self.taskMgr, self.rootAssetFolder + "/DroneDefender/DroneDefender.obj",
            self.render, "Drone", 6.0, self.rootAssetFolder + "/DroneDefender/octotoad1_auv.png",
            self.Planet2, 500, "Cloud", self.Hero
        )

        self.EnableHUD()
        self.planets = [self.Planet1, self.Planet2, self.Planet3, self.Planet4, self.Planet5, self.Planet6]

    def UpdateCamera(self, task):
        self.disableMouse()
        self.camera.reparentTo(self.Hero.modelNode)
        self.camera.setFluidPos(0, 1, 0)
        return task.cont

    def SetupCollisions(self):
        self.pusher.addCollider(self.Hero.collisionNode, self.Hero.modelNode)
        self.cTrav.addCollider(self.Hero.collisionNode, self.pusher)

        solid_objects = [self.Planet1, self.Planet2, self.Planet3, self.Planet4, self.Planet5, self.Planet6, self.SpaceStation1]
        for obj in solid_objects:
            self.pusher.addCollider(obj.collisionNode, obj.modelNode)
            self.cTrav.addCollider(obj.collisionNode, self.pusher)

        if self.SpaceStation1:
            self.cTrav.addCollider(self.SpaceStation1.collisionNode, self.collisionHandler)

        for drone in Drone.droneInstances:
            self.pusher.addCollider(drone.collisionNode, drone.modelNode)
            self.cTrav.addCollider(drone.collisionNode, self.collisionHandler)
            event_name = f'Missile*_cNode-into-{drone.modelNode.getName()}_cNode'
            self.accept(event_name, self.OnMissileHitsDrone)

        self.collisionHandler.addInPattern('%fn-into-%in')
        self.collisionHandler.addOutPattern('%fn-out-%in')

        self.cTrav.addCollider(self.Universe.collisionNode, self.collisionHandler)

        self.accept('Hero_cNode-into-Universe_cNode', self.onUniverseBoundary)
        self.accept('Missile*_cNode-into-SpaceStation1_cNode', self.OnMissileHitsSpaceStation)

    def OnMissileHitsDrone(self, entry):
        intoNP = entry.getIntoNodePath().getParent()
        for drone in Drone.droneInstances:
            if drone.modelNode == intoNP:
                drone.explode()
            break
        entry.getFromNodePath().getParent().removeNode()  # remove missile

    def onUniverseBoundary(self, entry):
        print("Object hit universe boundary!")

    def OnMissileHitsSpaceStation(self, entry):
        fromNode = entry.getFromNodePath().getParent()
        intoNode = entry.getIntoNodePath()
        print(f"Missile hit space station: {fromNode.getName()}, {intoNode.getName()}")
        fromNode.removeNode()
        self.SpaceStation1.modelNode.removeNode()
        print("Space station destroyed!")

    def SetKeyBindings(self):
        self.accept('a', self.Hero.turn_left, [1])
        self.accept('a-up', self.Hero.turn_left, [0])
        self.accept('d', self.Hero.turn_right, [1])
        self.accept('d-up', self.Hero.turn_right, [0])
        self.accept('s', self.Hero.move_forward, [1])
        self.accept('s-up', self.Hero.move_forward, [0])
        self.accept('w', self.Hero.turn_up, [1])
        self.accept('w-up', self.Hero.turn_up, [0])
        self.accept('x', self.Hero.turn_down, [1])
        self.accept('x-up', self.Hero.turn_down, [0])
        self.accept('shift', self.Hero.Boost)
        self.accept('r', self.StartPlanetRotation)
        self.accept('space', self.Hero.Fire)

    def RotatePlanets(self, task):
        for planet in self.planets:
            planet.modelNode.setH(planet.modelNode.getH() + 0.2)
        return task.cont

    def StartPlanetRotation(self):
        if not hasattr(self, 'planetRotationTask'):
            self.planetRotationTask = self.taskMgr.add(self.RotatePlanets, "rotate-planets")

    def StopPlanetRotation(self):
        if hasattr(self, 'planetRotationTask'):
            self.taskMgr.remove("rotate-planets")
            del self.planetRotationTask

    def updateBoostDisplay(self, status):
        if status == "READY":
            self.boostText.setText("Boost: READY")
        elif status == "ACTIVE":
            self.boostText.setText("Boost: ACTIVE")
        elif status == "COOLDOWN":
            self.boostText.setText("Boost: COOLDOWN")

    def EnableHUD(self):
        self.hud = OnscreenImage(image="./Assets/Hud/Reticleiv.jpg", pos=Vec3(0, 0, 0), scale=0.1)
        self.hud.setTransparency(TransparencyAttrib.MAlpha)

    def DrawBaseballSeams(self, centralObject, droneName, step, numSeams, radius=1):
        unitVec = defensePaths.BaseballSeams(step, numSeams, B=0.4)
        unitVec.normalize()
        position = unitVec * radius * 10
        SpaceJamClasses.Drone(
            self.loader, "./Assets/DroneDefender/DroneDefender.obj", centralObject.modelNode, droneName,
            "./Assets/DroneDefender/octotoad1_auv.png", position, 1
        )

    def DrawCloudDefense(self, centralObject, droneName):
        unitVec = defensePaths.Cloud()
        unitVec.normalize()
        position = unitVec * 10
        SpaceJamClasses.Drone(
            self.loader, "./Assets/DroneDefender/DroneDefender.obj", centralObject.modelNode, droneName,
            "./Assets/DroneDefender/octotoad1_auv.png", position, 1
        )


app = MyApp()

fullCycle = 60
for j in range(fullCycle):
    SpaceJamClasses.Drone.droneCount += 1
    nickName = "Drone" + str(SpaceJamClasses.Drone.droneCount)
    app.DrawCloudDefense(app.Planet1, nickName)
    app.DrawBaseballSeams(app.SpaceStation1, nickName, j, fullCycle, 2)

app.run()
