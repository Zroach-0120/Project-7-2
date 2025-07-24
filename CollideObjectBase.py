from panda3d.core import PandaNode, Loader, NodePath, CollisionNode, CollisionSphere, CollisionInvSphere, CollisionCapsule, Vec3

class PlacedObject(PandaNode):  
    def __init__(self, loader: Loader, modelPath: str, parentNode: NodePath, nodeName: str):
        self.modelNode: NodePath = loader.loadModel(modelPath)

        if not isinstance(self.modelNode, NodePath):
            raise AssertionError("PlacedObject loader.loadModel(" + modelPath + ") did not return a proper NodePath!")
        
        self.modelNode.reparentTo(parentNode)
        self.modelNode.setName(nodeName)

class CollideableObject(PlacedObject):
    def __init__(self, loader: Loader, modelPath: str, parentNode: NodePath, nodeName: str):
        super(CollideableObject, self).__init__(loader, modelPath, parentNode, nodeName)

        self.collisionNode = self.modelNode.attachNewNode(CollisionNode(nodeName + '_cNode'))
        
        self.collisionNode.show()
    
class InverseSphereCollideObject(CollideableObject):
    def __init__(self, loader: Loader, modelPath: str, parentNode: NodePath, nodeName: str, colPositionVec: Vec3, colRadius: float):
        super(InverseSphereCollideObject, self).__init__(loader, modelPath, parentNode, nodeName)
        self.collisionNode.node().addSolid(CollisionInvSphere(colPositionVec, colRadius))
        self.collisionNode.show()

class SphereCollideObject(CollideableObject):
    def __init__(self, loader: Loader, modelPath: str, parentNode: NodePath, nodeName: str, colPositionVec: Vec3, colRadius: float):
        super(SphereCollideObject, self).__init__(loader, modelPath, parentNode, nodeName)
        self.collisionNode.node().addSolid(CollisionSphere(colPositionVec, colRadius))
        self.collisionNode.show()

class CapsuleCollideableObject(CollideableObject):
    def __init__(self, loader: Loader, modelPath: str, parentNode: NodePath, nodeName: str, ax: float, ay: float, az: float, bx: float, by: float, bz: float, r: float):
        super(CapsuleCollideableObject, self).__init__(loader, modelPath, parentNode, nodeName)
        self.collisionNode.node().addSolid(CollisionCapsule(ax, ay, az, bx, by, bz, r))
        self.collisionNode.show()
