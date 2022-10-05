## when you change any of these, update the shas as well
let BASH_NAME="bash-4.4";  # TODO: 5.1 upgrade
BUSYBOX_NAME="busybox-1.35.0";
DASH_NAME="dash-0.5.10.2";
YASH_NAME="yash-2.49";
in
self: super: {
  # https://tiswww.case.edu/php/chet/bash/bashtop.html - 9/2016 release
  # https://ftp.gnu.org/gnu/bash/
#  oiltest_bash = super.bashInteractive_5.overrideAttrs (oldAttrs: rec {
#    version = "5.1";
#    name="oiltest_bash-5.1";
#    src = super.fetchurl {
#      url = "https://ftp.gnu.org/gnu/bash/bash-5.1.tar.gz";
#      sha256 = "1alv68wplnfdm6mh39hm57060xgssb9vqca4yr1cyva0c342n0fc";
#    };
#    patches = [ ];
#  });
  oiltest_bash = super.stdenv.mkDerivation {
    name="oiltest_${BASH_NAME}";
    src = super.fetchurl {
      url = "https://www.oilshell.org/blob/spec-bin/${BASH_NAME}.tar.gz";
      sha256 = "1jyz6snd63xjn6skk7za6psgidsd53k05cr3lksqybi0q6936syq";
    };
  };

  oiltest_dash = super.stdenv.mkDerivation {
    name="oiltest_${DASH_NAME}";
    # dash uses non-literal format strings
    hardeningDisable = [ "format" ];
    src = super.fetchurl {
      url = "https://www.oilshell.org/blob/spec-bin/${DASH_NAME}.tar.gz";
      sha256 = "0wb0bwmqc661hylqcfdp7l7x12myw3vpqk513ncyqrjwvhckjriw";
    };
  };

  oiltest_yash = super.stdenv.mkDerivation {
    name="oiltest_${YASH_NAME}";
    # dash uses non-literal format strings
    hardeningDisable = [ "format" ];
    configureFlags = [ "--disable-lineedit" ];
    src = super.fetchurl {
      url = "https://www.oilshell.org/blob/spec-bin/${YASH_NAME}.tar.xz";
      sha256 = "0wlw46f2xnr1w5smhy00mr71w5dfb4bnj09qa2knb4bldhfz3sk6";
    };
  };

  oiltest_zsh = super.stdenv.mkDerivation {
    name="oiltest_zsh-5.1.1";
    # dash uses non-literal format strings
    hardeningDisable = [ "format" ];
    configureFlags = [ "--disable-dynamic" "--with-tcsetpgrp" ];
    buildInputs = [ super.ncurses ];
    src = super.fetchurl {
      url = "https://www.oilshell.org/blob/spec-bin/zsh-5.1.1.tar.xz";
      sha256 = "1v1xilz0fl9r9c7dr2lnn7bw6hfj0gbcz4wz1ybw1cvhahxlbsbl";
    };
  };

  oiltest_mksh = super.stdenv.mkDerivation {
    name="oiltest_mksh-R52c";
    # dash uses non-literal format strings
    hardeningDisable = [ "format" ];

    dontConfigure = true;

    installPhase = ''
      runHook preInstall
      install -D mksh $out/bin/mksh
      install -D dot.mkshrc $out/share/mksh/mkshrc
      runHook postInstall
    '';
    buildPhase = ''
      runHook preBuild
      sh ./Build.sh -r
      runHook postBuild
    '';

    src = super.fetchurl {
      url = "https://www.oilshell.org/blob/spec-bin/mksh-R52c.tgz";
      sha256 = "19ivsic15903hv3ipzk0kvkaxardw7b99s8l5iw3y415lz71ld66";
    };
  };


  # https://www.mirbsd.org/mksh.htm
  #_wget https://www.mirbsd.org/MirOS/dist/mir/mksh/mksh-R59.tgz

  # https://tracker.debian.org/pkg/dash  -- old versions
  # http://www.linuxfromscratch.org/blfs/view/svn/postlfs/dash.html
  #_wget http://gondor.apana.org.au/~herbert/dash/files/dash-0.5.10.2.tar.gz

  # http://zsh.sourceforge.net/News/ - 12/2016 release
  #_wget https://downloads.sourceforge.net/project/zsh/zsh/5.8.1/zsh-5.8.1.tar.xz

  #_wget https://osdn.net/dl/yash/yash-2.49.tar.xz

  #_wget https://www.busybox.net/downloads/busybox-1.35.0.tar.bz2
}
