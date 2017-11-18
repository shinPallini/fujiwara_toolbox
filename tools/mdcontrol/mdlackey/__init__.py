import os
import lackey
from lackey import *

import sys
sys.path.append(os.pardir)
import uwscwrapper as uwsc


def check_abort():
    loc = Mouse().getPos()
    if loc.getX() == 0 and loc.getY() == 0:
        print("abort.")
        sys.exit()


class MD():
    """
        MarvelousDesigner操作用クラス。
    """
    def __init__(self):
        app = App("Marvelous Designer")
        self.is_initialized = False
        if not app.isRunning():
            return
        self.is_initialized = True
        self.app = app

        self.ver = "7"
        title = app.getWindow()
        self.title = title
        if "7" in title:
            self.ver = "7"
        if "6.5" in title:
            self.ver = "6.5"

        self.scale = "100%"

        Settings.MoveMouseDelay = 0.01

        self.set_scale("file")

    @classmethod
    def wait(self, time):
        App.pause(time)

    def imgpath(self, filename):
        moddir = os.path.dirname(__file__)
        path = "img" + os.sep + str(self.ver) + os.sep + "jp" + os.sep + self.scale + os.sep
        return moddir + os.sep + path + filename + ".png"

    def activate(self):
        if check_abort():
            return
        """
            uwscwrapperをつかったウィンドウのアクティベート。
        """
        print(self.title)
        uwsc.activate(self.title)
        self.wait(1)

    def set_scale(self, filename):
        """
            各スケール画像で検索して、倍率を確定する。
        """
        scale_list = ["100%", "125%", "150%", "175%", "200%"]
        self.activate()
        region = App.focusedWindow().getScreen()

        for scale in scale_list:
            self.scale = scale

            img = self.imgpath(filename)

            if os.path.exists(img):
                m = region.exists(img)

                if m is not None:
                    return
        
        #なかったのでデフォルトに戻す
        self.scale = "100%"

    def find(self, filename):
        return self.click(filename, False)

    def click(self, filename, click=True):
        if check_abort():
            print("aboted.")
            return False

        img = self.imgpath(filename)
        # pat = Pattern(self.imgpath(filename))
        # img = pat.similar(0.5)

        # if search_screen:
        #     region = App.focusedWindow().getScreen()
        # else:
        #     region = App.focusedWindow()
        
        # active_screen_id = App.focusedWindow().getScreen().getID()
        # #全スクリーンを検索する。
        # screens_n = Screen.getNumberScreens() - 1
        # scrn_list = [active_screen_id]
        # for i in range(screens_n):
        #     if i not in scrn_list:
        #         scrn_list.append(i)

        # for i in scrn_list:
        #     region = Screen(i)
        #     m = region.exists(img)
        #     if m is not None:
        #         break
        # 負の座標のスクリーンで問題が起こる。



        #テスト
        # Screen.showMonitors()
        # print("*****----------------------")
        # screens_n = Screen.getNumberScreens()
        # print(screens_n)
        # for i in range(screens_n):
        #     print(Screen(i).getBounds())
        # print("----------------------*****")

        # ##################
        # screens_n = Screen.getNumberScreens()
        # for i in range(screens_n):
        #     m = Screen(i).exists(img)
        #     if m is not None:
        #         break
        # ##################

        region = App.focusedWindow().getScreen()
        m = region.exists(img)

        if m is not None:
            if click:
                region.click(m)
            print(filename)
            return True
        return False

    # def click_untill_success(self, filename):
    #     for i in range(100):
    #         c = self.click(filename)
    #         if c is not None:
    #             return True
    #         self.wait(0.1)
    #     return False

    def click_untill_imgfound(self, filename, searchfor):
        for i in range(100):
            f = self.find(searchfor)
            if f is not None:
                return True

            self.click(filename)
            self.wait(0.5)
        return False
        


class MDMacro():
    md = None

    @classmethod
    def md_setup(cls):
        if cls.md == None:
            cls.md = MD()
        return cls.md

    @classmethod
    def wait(self, time):
        MD.wait(time)

    @classmethod
    def macro_test(self):
        md = MDMacro.md_setup()
        if not md.is_initialized:
            return()
        if not md.click("file"):
            return
        md.click("new_file")
        md.click("no")
        md.click("file")
        md.click("import")
        md.click("obj")
        # md.click("")

    @classmethod
    def new_file(self):
        md = MDMacro.md_setup()
        if not md.is_initialized:
            print("###MD is not initialized.")
            return()
        md.activate()
        if not md.click("file"):
            return
        md.click("new_file")
        md.click("no")

    @classmethod
    def paste_str(self, str):
        App.setClipboard(str)
        type("v", KeyModifier.CTRL)
        type(Key.ENTER)

    @classmethod
    def open_avatar(self,filepath):
        md = MDMacro.md_setup()
        if not md.is_initialized:
            print("###MD is not initialized.")
            return()

        if not md.click("file"):
            return
        md.click("import")
        md.click("obj")

        # uwsc.click_item(filename)
        MD.wait(0.5)
        self.paste_str(filepath)

        md.click("ok")
        md.click("close")
        md.activate()

    @classmethod
    def open_avatar_abc(self, filepath):
        md = MDMacro.md_setup()
        if not md.is_initialized:
            print("###MD is not initialized.")
            return()

        if not md.click("file"):
            return
        md.click("import")
        md.click("alembic")

        # uwsc.click_item(filename)
        MD.wait(0.5)
        self.paste_str(filepath)
        md.click("m")
        md.click("ok")
        md.click("close")
        md.activate()

    @classmethod
    def add_garment(self, filepath):
        md = MDMacro.md_setup()
        if not md.is_initialized:
            print("###MD is not initialized.")
            return

        #成功するまでトライ
        for i in range(30):
            md.activate()
            md.click("file")
            c = md.click("add")

            if c:
                break
            md.wait(0.5)

        md.click("garment")

        MD.wait(0.5)
        self.paste_str(filepath)

    @classmethod
    def add_mdd(self, filepath):
        md = MDMacro.md_setup()
        if not md.is_initialized:
            print("###MD is not initialized.")
            return()

        md.activate()

        if not md.click("file"):
            return
        md.click("import")
        md.click("mdd_chache_default")

        MD.wait(0.5)
        self.paste_str(filepath)
        md.click("m")
        md.click("ok")

    @classmethod
    def simulate(self, time):
        md = MDMacro.md_setup()
        if not md.is_initialized:
            print("###MD is not initialized.")
            return

        md.activate()

        for i in range(30):
            md.activate()
            md.click("3dgarment")
            md.click("simulation_off")
            f = md.find("sim_on")

            if f:
                break
            md.wait(0.5)

        for i in range(30):
            md.activate()
            md.click("avatar")
            md.click("play_motion_off")
            f = md.find("anim_on")

            if f:
                break
            md.wait(0.5)

        MD.wait(time)

        for i in range(30):
            md.activate()
            md.click("3dgarment")
            md.click("simulation_on")
            f = md.find("sim_off")

            if f:
                break
            md.wait(0.5)

    @classmethod
    def select_all(self):
        md = MDMacro.md_setup()
        if not md.is_initialized:
            return

        md.activate()
        type("a",Key.CTRL)

    @classmethod
    def export_obj(self, filepath, use_thickness):
        md = MDMacro.md_setup()
        if not md.is_initialized:
            print("###MD is not initialized.")
            return

        md.activate()
        md.click("file")
        md.click("export")
        md.click("obj_selected_only")
        MD.wait(0.5)
        self.paste_str(filepath)
        MD.wait(0.5)
        uwsc.click_item("はい")
        MD.wait(0.5)
        md.click("single_object")
        # md.click("combine_objects")
        if use_thickness:
            md.click("thick")
        md.click("m")
        md.click("ok")

    @classmethod
    def export_abc(self, filepath):
        md = MDMacro.md_setup()
        if not md.is_initialized:
            print("###MD is not initialized.")
            return

        md.activate()
        md.click("file")
        md.click("export")
        md.click("alembic_ogawa")
        MD.wait(0.5)
        self.paste_str(filepath)
        uwsc.click_item("はい")
        MD.wait(1)
        md.click("single_object")
        if use_thickness:
            md.click("thick")
        md.click("m")
        md.click("ok")
