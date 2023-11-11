# CuraSolidWorksPlugin

updated existing solidworks plugin based on following reddit thread:

https://www.reddit.com/r/Cura/comments/vggogm/solidworks_plugin/

Cura needs to be installed using the exe installer, not the MSI, because of how the script finds the install directory using the registry key for uninstalling Cura. The exe installer puts the uninstall key where this script expects it to be, the msi installer does not. 
