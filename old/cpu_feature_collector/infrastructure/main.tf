provider "aws" {
  profile = "default"
  region  = var.region
}

module "read-instances" {
  source    = "./modules/read-instances"
  file_path = "AWS x86 instances(us-west-2, feature group).csv"
}

module "vpc" {
  source            = "./modules/VPC"
  resource_prefix   = var.resource_prefix
  availability_zone = var.availability_zone
}

module "ec2" {
  source            = "./modules/EC2"
  instance_group    = module.read-instances.instance_group
  ami_id            = var.ami_id
  key_name          = var.key_name
  availability_zone = var.availability_zone
  public_subnet_id  = module.vpc.public_subnet_id
  security_group_id = aws_security_group.ec2_security_group.id
  user              = var.user
  resource_prefix   = var.resource_prefix
  ec2_instance_profile = aws_iam_instance_profile.instance-profile.name

  depends_on = [
    module.read-instances,
  ]
}
