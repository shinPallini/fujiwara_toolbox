﻿import bpy
#パス関連のユーティリティ
#http://xwave.exblog.jp/7155003
import os.path
import os
import re
import bmesh
import datetime
import subprocess
import shutil
import time
import copy
import sys
import mathutils
from collections import OrderedDict
import inspect

# import bpy.mathutils.Vector as Vector
from mathutils import Vector

from bpy.props import (StringProperty,
                       BoolProperty,
                       IntProperty,
                       FloatProperty,
                       FloatVectorProperty,
                       EnumProperty,
                       PointerProperty,
                       )
from bpy.types import (Panel,
                       Operator,
                       AddonPreferences,
                       PropertyGroup,
                       )


fujiwara_toolbox = __import__(__package__)
try:
    from fujiwara_toolbox import fjw #コード補完用
except:
    fjw = fujiwara_toolbox.fjw


import random
from mathutils import *


"""
MarvelousDesignerまわりの仕様
カスタムプロパティを使用してコントロールする。

基本設定
md_garment_path_list   ["pathA", "pathB", "pathC"]ってかんじでカスタムプロパティに打ち込む。
                        追加はコマンドから行った方がよさそう。ファイルブラウザで。
md_export_id int このパーツのエクスポートID　このプロパティがあったらアバターとして出力する

運用設定
md_garment_index    パスリストの何番目の衣装を使うか。なければ-1として扱う。
                    ない場合はリンク先フォルダの同名.zpacを使う。
md_export_depth     intかintのlist
                    IDのどのレベルまでエクスポートするか。
                    listだった場合は該当レベルを個別に有効にする。
                    なければ0。
こっちの値、作業ファイル準備時に反映しなければならない！

カスタムプロパティはいずれのオブジェクトにつけてもいい。
MDObjectにわたされたオブジェクト群の中で検索する。
"""

class MDObject():
    """
        MarvelousDesignerエクスポート用のデータ。
    """

    def __init__(self, mdname, objects, garment_path="", export_dir="MDData"):
        """
            エクスポートオブジェクトの名前
            オブジェクトのリスト
        """
        self.mdname = mdname
        self.objects = objects
        if export_dir == "MDData":
            blendname = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
            self.__set_export_dir(self.__get_mddatadir() + os.sep + blendname.replace("_MDWork", "") + os.sep + mdname)
        else:
            self.export_dir = export_dir

        if garment_path == "":
            self.garment_path = self.get_garment_path()
        else:
            self.garment_path = garment_path

    def has_obj(self, obj):
        if obj in self.objects:
            return True
        return False

    def get_garment_path(self):
        garment_list = self.__get_prop_from_objects("md_garment_path_list")
        garment_index = self.__get_prop_from_objects("md_garment_index")
        if garment_list is None:
            #デフォルトパスをリンクから取得してみる
            linked_path = self.__get_prop_from_objects("linked_path")
            if linked_path is not None:
                linked_dir = os.path.dirname(linked_path)
                garment_path = linked_dir + os.sep + self.mdname + ".zpac"
                if not os.path.exists(garment_path):
                    return None
                return garment_path
            else:
                return None
        else:
            if garment_index is None:
                garment_index = 0
            if garment_index >= len(garment_list):
                garment_index = 0
            return garment_list[garment_index]

    def get_export_objects(self):
        index_list = self.__get_export_index_list()
        objects = self.__filter_objects("MESH")
        result = []
        for obj in objects:
            if "md_export_id" in obj:
                if obj["md_export_id"] in index_list:
                    result.append(obj)

        #もしresultが空なら、次はBodyを検索する。
        if len(result) == 0:
            for obj in objects:
                if "Body" in obj.name:
                    result.append(obj)

        #なければ、選択オブジェクトをそのまま採用する。
        if len(result) == 0:
            result.extend(objects)
        

        return result

    # def export_obj(self, dirpath, animation=True):
    #     """
    #         .obj+.mddを出力
    #     """
    #     self.__export_setup(dirpath)
    #     #obj出力
    #     bpy.ops.export_scene.obj(filepath= self.export_dir + os.sep + self.mdname + ".obj", use_selection=True)
    #     if animation:
    #         #PointCache出力
    #         bpy.ops.export_shape.mdd(filepath= self.export_dir + os.sep + self.mdname + ".mdd", fps=6,frame_start=1,frame_end=10)
    
    def export_abc(self, dirpath):
        self.__export_setup(dirpath)
        path = os.path.normpath(self.export_dir + os.sep + self.mdname + ".abc")
        print("export abc:%s"%path)
        bpy.ops.wm.alembic_export(filepath=path, start=1, end=20, selected=True, visible_layers_only=True, flatten=True, apply_subdiv=True, compression_type='OGAWA', as_background_job=False)

    def export_to_mddata(self):
        self.export_abc(self.export_dir)
        self.export_mddatafile()

    def open_export_dir(self):
        os.system("EXPLORER " + self.export_dir)

    def get_sim_path(self):
        toolpath = fujiwara_toolbox.__path__[0] + os.sep + "tools" + os.sep + "mdcontrol" + os.sep + "mdcontrol.py"
        avatar_path = os.path.normpath(self.export_dir + os.sep + self.mdname + ".abc")
        animation_path = "none"
        garment_path = os.path.normpath(self.get_garment_path())
        result_path = os.path.normpath(self.export_dir + os.sep + "result.obj")
        return toolpath, avatar_path, animation_path, garment_path, result_path

    def export_mddatafile(self):
        toolpath, avatar_path, animation_path, garment_path, result_path = self.get_sim_path()

        data = ""
        data += 'avatar_path="%s"\n'%avatar_path
        data += 'garment_path="%s"\n'%garment_path
        data += 'result_path="%s"\n'%result_path
        data += 'mddatafiles.append((avatar_path, garment_path, result_path))\n'
        
        datafilepath = os.path.normpath(self.export_dir + os.sep + self.mdname + "_mddata.py")
        
        f = open(datafilepath, "w")
        f.write(data)
        f.close()


    def md_sim(self):
        """
            アバター .obj
            アニメーション .mdd
            衣装ファイル.zpac
            リザルトパス
        """
        (toolpath, avatar_path, animation_path, garment_path, result_path) = self.get_sim_path()
        # toolpath = os.path.basename(fjw.__file__) + os.sep + "tools" + os.sep + "mdcontrol" + os.sep + "mdcontrol.py"

        cmdstr = 'python "%s" "%s" "%s" "%s" "%s"'%(toolpath, avatar_path, animation_path, garment_path, result_path)
        print(cmdstr)
        p = subprocess.Popen(cmdstr)
        p.wait(5*60)
        print("mdsim done.")
        return

    def __set_export_dir(self, dirpath):
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)
        self.export_dir = dirpath

    def __filter_objects(self, object_type):
        result = []
        for obj in self.objects:
            if obj.type == object_type:
                result.append(obj)
        return result

    def __get_mddatadir(self):
        return os.path.dirname(bpy.data.filepath) + os.sep + "MDData"+ os.sep

    def __export_setup(self, dirpath):
        fjw.deselect()
        fjw.select(self.get_export_objects())
        self.__simplify(2)
        for obj in self.objects:
            self.__disable_backsurface_edge(obj)
        #フレーム1に移動
        bpy.ops.screen.frame_jump(end=False)

    def __simplify(self, level):
        #簡略化2
        if not bpy.context.scene.render.use_simplify:
            bpy.context.scene.render.use_simplify = True
        if bpy.context.scene.render.simplify_subdivision != level:
            bpy.context.scene.render.simplify_subdivision = level

    def __disable_backsurface_edge(self, obj):
        #裏ポリエッジオフ
        for mod in obj.modifiers:
            if "裏ポリエッジ" in mod.name:
                mod.show_viewport = False
                mod.show_render = False

    def __get_prop_from_objects(self, propname):
        result = None
        for obj in self.objects:
            if propname in obj:
                result = obj[propname]
                break
        return result

    def __get_export_index_list(self):
        export_index_list = None
        export_depth = self.__get_prop_from_objects("md_export_depth")
        if export_depth is None:
            export_index_list = [0]
        else:
            if type(export_depth) == list:
                export_index_list = export_depth
            if type(export_depth) == int:
                export_index_list = []
                for i in range(export_depth):
                    export_index_list.append(i)
        return export_index_list

class MDObjectManager():
    def __init__(self):
        self.mdobjects = []

    def is_already_registerd(self, obj):
        for mdo in self.mdobjects:
            if mdo.has_obj(obj):
                return True
        return False

    def find_mdobj_by_object(self, obj):
        for mdo in self.mdobjects:
            if mdo.has_obj(obj):
                return mdo
        return None

    def get_avatar_objects_from_its_root(self, child_object):
        """
            オブジェクトからルートオブジェクトを取得して、
            mdobjectsに格納する。
        """
        fjw.deselect()
        root = fjw.get_root(child_object)

        mdobj = self.find_mdobj_by_object(root)
        if mdobj is not None:
            return mdobj

        fjw.activate(root)
        rootname = re.sub("\.\d+", "", root.name)
        bpy.ops.fujiwara_toolbox.command_24259()#親子選択
        selection = fjw.get_selected_list()
        mdobj = MDObject(rootname, selection)
        self.mdobjects.append(mdobj)

        return mdobj        

    def export_mdavatar(self, objects, run_simulate=False):
        self.mdobjects = []
        for obj in objects:
            mdobj = self.get_avatar_objects_from_its_root(obj)

        for mdobj in self.mdobjects:
            mdobj.export_to_mddata()

        if run_simulate:
            for mdobj in self.mdobjects:
                mdobj.md_sim()

    def export_active_body_mdavatar(self, run_simulate=False):
        active = fjw.active()
        self.export_mdavatar([active], run_simulate)

    def export_selected_mdavatar(self, run_simulate=False):
        selection = fjw.get_selected_list()
        self.export_mdavatar(selection, run_simulate)

    #なんか危険な予感がする。リンクオブジェクトとか。
    # def export_all_mdavatar(self, run_simulate=False):
    #     self.export_mdavatar(bpy.context.scene.objects, run_simulate)

class MarvelousDesingerUtils():
    def __init__(self):
        self.mddata_dir = self.get_mddatadir()

    @classmethod
    def export_active(self, run_simulate=False):
        mdmanager = MDObjectManager()
        mdmanager.export_active_body_mdavatar(run_simulate)

    @classmethod
    def export_selected(self, run_simulate=False):
        mdmanager = MDObjectManager()
        mdmanager.export_selected_mdavatar(run_simulate)

    @classmethod
    def setkey(cls):
        if fjw.active().type == "ARMATURE":
            fjw.mode("POSE")
        if fjw.active().mode == "OBJECT":
            bpy.ops.anim.keyframe_insert_menu(type='LocRotScale')
        if fjw.active().mode == "POSE":
            #MarvelousDesigner用
            aau = fjw.ArmatureActionUtils(fjw.active())
            aau.set_action("mdwork")
            frame = bpy.context.scene.frame_current
            aau.store_pose(frame, "mdpose_"+str(frame))

            bpy.ops.pose.select_all(action='SELECT')
            bpy.ops.anim.keyframe_insert_menu(type='WholeCharacter')

    @classmethod
    def delkey(cls):
        if fjw.active().type == "ARMATURE":
            fjw.mode("POSE")
        if fjw.active().mode == "OBJECT":
            bpy.ops.anim.keyframe_delete_v3d()
        if fjw.active().mode == "POSE":
            #MarvelousDesigner用
            aau = fjw.ArmatureActionUtils(fjw.active())
            aau.set_action("mdwork")
            frame = bpy.context.scene.frame_current
            aau.delete_pose("mdpose_"+str(frame))        

            bpy.ops.pose.select_all(action='SELECT')
            bpy.ops.anim.keyframe_delete_v3d()

    @classmethod
    def armature_autokey(cls):
        """
        アーマチュアのキーをオートで入れる
        """
        if fjw.active().type != "ARMATURE":
            return

        fjw.mode("POSE")

        #アーマチュアのキーをオートで入れる
        if bpy.context.scene.frame_current == 10:
            rootname = fjw.get_root(fjw.active()).name

            fjw.active().location = Vector((0,0,0))

            cls.setkey()

            #フレーム10なら微調整じゃないのでオートフレーム。
            armu = fjw.ArmatureUtils(fjw.active())
            geo = armu.GetGeometryBone()
            armu.clearTrans([geo])

            cls.setkey()

            fjw.framejump(1)
            selection = armu.select_all()
            armu.clearTrans(selection)

            cls.setkey()

            #選択にズーム
            bpy.ops.view3d.view_selected(use_all_regions=False)
            fjw.framejump(10)

    @classmethod
    def import_mdresult(cls,resultpath, attouch_fjwset=False):
        if not os.path.exists(resultpath):
            return

        current = fjw.active()

        loc = Vector((0,0,0))
        qrot = Quaternion((0,0,0,0))

        bonemode = False
        #もしボーンが選択されていたらそのボーンにトランスフォームをあわせる
        if current is not None and current.mode == "POSE":
            armu = fjw.ArmatureUtils(current)
            pbone = armu.poseactive()
            armu.get_pbone_world_co(pbone.head)
            loc = armu.get_pbone_world_co(pbone.head)
            qrot = pbone.rotation_quaternion

            #boneはYupなので入れ替え
            qrot = Quaternion((qrot.w, qrot.x, qrot.z * -1, qrot.y))
            bonemonde = True

        fjw.mode("OBJECT")

        fname, ext = os.path.splitext(resultpath)
        if ext == ".obj":
            bpy.ops.import_scene.obj(filepath=resultpath)
        if ext == ".abc":
            bpy.ops.wm.alembic_import(filepath=resultpath, as_background_job=False)
            selection = fjw.get_selected_list()
            for obj in selection:
                obj.name = "result"


        #インポート後処理
        #回転を適用
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

        selection = fjw.get_selected_list()
        for obj in selection:
            if obj.type == "MESH":
                bpy.context.scene.objects.active = obj
                bpy.ops.object.mode_set(mode='EDIT', toggle=False)
                bpy.ops.mesh.remove_doubles()
                bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
                
                # #服はエッジ出ない方がいい 裏ポリで十分
                # for slot in obj.material_slots:
                #     mat = slot.material
                #     mat.use_transparency = True
                #     mat.transparency_method = 'RAYTRACE'

                obj.location = loc
                if bonemode:
                    obj.rotation_quaternion = obj.rotation_quaternion * qrot
                    obj.rotation_euler = obj.rotation_quaternion.to_euler()
        
                #読み先にレイヤーをそろえる
                if current is not None:
                    obj.layers = current.layers
        
        if attouch_fjwset:
            bpy.ops.fujiwara_toolbox.command_318722()#裏ポリエッジ付加
            bpy.ops.fujiwara_toolbox.set_thickness_driver_with_empty_auto() #指定Emptyで厚み制御


    @classmethod
    def mdresult_auto_import_main(cls, self, context, attouch_fjwset=False):
        import_ext = ".obj"


        #存在確認
        blendname = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
        dir = os.path.dirname(bpy.data.filepath) + os.sep + "MDData" + os.sep + blendname + os.sep
        self.report({"INFO"},dir)

        if not os.path.exists(dir):
            self.report({"INFO"},"キャンセルされました。")
            bpy.ops.wm.quit_blender()
            return {'CANCELLED'}

        #既存のリザルトを処分
        fjw.deselect()
        dellist = []
        for obj in bpy.context.scene.objects:
            if obj.type == "MESH" and "result" in obj.name:
                dellist.append(obj)
        fjw.delete(dellist)

        root_objects = []
        for obj in bpy.context.scene.objects:
            if obj.parent is None:
                root_objects.append(obj)

        files = os.listdir(dir)
        for file in files:
            self.report({"INFO"},file)
            print("MDResult found:"+file)
            targetname = file

            # rootobjでの設置だとルートがないとおかしなことになる
            # dupli_groupの名前でみて、同一名のもののアーマチュアを探して、
            # vislble_objects内のそのデータと同一のプロクシないしアーマチュア、のジオメトリを指定すればいいのでは

            #fileと同名のdupli_groupを検索
            if targetname in bpy.data.groups:
                dgroup = bpy.data.groups[targetname]
                #Bodyが参照しているアーマチュアのデータを取得
                target_armature = None
                if "Body" in dgroup.objects:
                    Body = dgroup.objects["Body"]
                    modu = fjw.Modutils(Body)
                    armt = modu.find("Armature")
                    if armt is not None:
                        armature = armt.object
                        if armature is not None:
                            armature_data = armature.data
                            for scene_amature in bpy.context.visible_objects:
                                if scene_amature.type != "ARMATURE":
                                    continue
                                if scene_amature.data != armature_data:
                                    continue
                                #同一のアーマチュアデータを発見したのでこいつを使用する
                                target_armature = scene_amature
                                break
                if target_armature is not None:
                    arm = target_armature
                    print("MDImport Step 0")
                    fjw.mode("OBJECT")
                    fjw.deselect()
                    fjw.activate(arm)
                    print("MDImport Step 1")
                    fjw.mode("POSE")
                    armu = fjw.ArmatureUtils(arm)
                    geo = armu.GetGeometryBone()
                    armu.activate(geo)
                    print("MDImport Step 2")
                    fjw.mode("POSE")

                    self.report({"INFO"},dir + file)
                    print("MDImport Selecting GeoBone:" + dir + file)

            #インポート
            mdresultpath = dir + file + os.sep + "result" + import_ext
            MarvelousDesingerUtils.import_mdresult(mdresultpath, attouch_fjwset)
            print("MDImport Import MDResult:"+mdresultpath)

        fjw.mode("OBJECT")
        for obj in bpy.context.visible_objects:
            if "result" in obj.name:
                obj.select = True
        if attouch_fjwset:
            bpy.ops.fujiwara_toolbox.comic_shader_nospec()

    @classmethod
    def __get_prop(cls, obj, name):
        """
        カスタムプロパティを取得する。
        なければNone
        """
        if name in obj:
            return obj[name]
        return None

    @classmethod
    def setup_mdwork_main(cls, self,context):
        if "_MDWork" not in bpy.data.filepath:
            fjw.framejump(10)
            dir = os.path.dirname(bpy.data.filepath)
            name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
            blend_md = dir + os.sep + name + "_MDWork.blend"
            bpy.ops.wm.save_as_mainfile(filepath=blend_md)

            bpy.context.scene.layers[0] = True
            for i in range(19):
                bpy.context.scene.layers[i + 1] = False
            for i in range(5):
                bpy.context.scene.layers[i] = True

            #ポーズだけついてるやつをポーズライブラリに登録する
            for armature_proxy in bpy.context.visible_objects:
                if armature_proxy.type != "ARMATURE":
                    continue
                if "_proxy" not in armature_proxy.name:
                    continue
                fjw.deselect()
                fjw.activate(armature_proxy)
                fjw.mode("POSE")
                bpy.ops.pose.select_all(action='SELECT')
                bpy.ops.fujiwara_toolbox.set_key()
                fjw.mode("OBJECT")

            fjw.mode("OBJECT")
            bpy.ops.object.select_all(action='SELECT')

            bpy.ops.file.make_paths_absolute()
            selection = fjw.get_selected_list()
            for obj in selection:
                md_garment_path_list = cls.__get_prop(obj, "md_garment_path_list")
                md_export_id = cls.__get_prop(obj, "md_export_id")
                md_garment_index = cls.__get_prop(obj, "md_garment_index")
                md_export_depth = cls.__get_prop(obj, "md_export_depth")

                # obj.dupli_group.library.filepath
                link_path = ""
                if obj.dupli_group is not None and obj.dupli_group.library is not None:
                    link_path = obj.dupli_group.library.filepath
                if link_path == "" or link_path is None:
                    continue

                fjw.deselect()
                fjw.activate(obj)
                bpy.ops.object.duplicates_make_real(use_base_parent=True,use_hierarchy=True)
                realized_objects = fjw.get_selected_list()
                for robj in realized_objects:
                    robj["linked_path"] = link_path

                    root = fjw.get_root(robj)
                    if md_garment_path_list is not None:
                        root["md_garment_path_list"] = md_garment_path_list
                    if md_export_id is not None:
                        root["md_export_id"] = md_export_id
                    if md_garment_index is not None:
                        root["md_garment_index"] = md_garment_index
                    if md_export_depth is not None:
                        root["md_export_depth"] = md_export_depth

            #proxyの処理
            #同一のアーマチュアデータを使っているものを探してポーズライブラリを設定する。
            for armature_proxy in bpy.data.objects:
                if armature_proxy.type != "ARMATURE":
                    continue
                if "_proxy" not in armature_proxy.name:
                    continue


                for armature in bpy.data.objects:
                    if armature.type != "ARMATURE":
                        continue
                    if armature == armature_proxy:
                        continue

                    if armature.data == armature_proxy.data:
                        #同一データを使用している
                        #のでポーズライブラリの設定をコピーする
                        armature.pose_library = armature_proxy.pose_library

                        #回収したポーズライブラリを反映する
                        fjw.mode("OBJECT")
                        fjw.activate(armature)
                        
                        if fjw.active() is not None:
                            aau = fjw.ArmatureActionUtils(armature)
                            armu = fjw.ArmatureUtils(armature)
                            
                            fjw.mode("POSE")
                            poselist = aau.get_poselist()
                            if poselist is not None:
                                for pose in aau.get_poselist():
                                    frame = int(str(pose.name).replace("mdpose_",""))
                                    fjw.framejump(frame)

                                    #ジオメトリはゼロ位置にする
                                    geo = armu.GetGeometryBone()
                                    armu.clearTrans([geo])
                                    bpy.ops.pose.select_all(action='SELECT')
                                    armu.databone(geo.name).select = False
                                    aau.apply_pose(pose.name)
                            #1フレームではデフォルトポーズに
                            fjw.mode("POSE")
                            fjw.framejump(1)
                            bpy.ops.pose.select_all(action='SELECT')
                            bpy.ops.pose.transforms_clear()

            #proxyの全削除
            fjw.mode("OBJECT")
            prxs = fjw.find_list("_proxy")
            fjw.delete(prxs)

            # bpy.app.handlers.scene_update_post.append(process_proxy)
            bpy.context.space_data.show_only_render = False
