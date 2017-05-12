 # Collada Exporter for Second Life - Blender Addon
 
 *NOTE: This is an early version, testing is in progress*


## Motivation

Recently, I've noticed that the default Collada exporter in Blender (2.78) has some problems to export textured objects for usage in Second Life. Particularly, I've reported these two issues:

* [Collada exporter assigns the same texture to all objects when they share the same material](https://developer.blender.org/T51259)

* [Collada exporter does not assign any texture when object has multiple UV maps](https://developer.blender.org/T51288)

Those issues prevent to quickly upload larger scenes (like a whole house) including all baked textures to SL and you need to apply textures by hand after upload, which is time wasting especially when you do many uploads to test your builds.

I wanted to try to fix these issues. But alas the default Collada exporter is made in C++ and I didn't want to recompile whole Blender. So, I decided to write my own Python based exporter that would work as an addon.


## Notes

* Export static mesh objects to Collada (.dae), including images assigned to the active UV layer.

* Tested with Firestorm Viewer for Second Life and InWorldz.

* Requires python collada module https://github.com/pycollada/pycollada. Pycollada is not a part of official Blender, so must be installed into Blender's folder (eg. Blender/2.78/scripts/modules)

