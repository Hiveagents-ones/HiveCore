package com.example.member.repository;

import com.example.member.entity.Member;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface MemberRepository extends JpaRepository<Member, Long> {

    /**
     * 根据联系方式查找会员
     * @param contact 联系方式
     * @return 会员信息
     */
    Optional<Member> findByContact(String contact);

    /**
     * 根据会员状态查找会员列表
     * @param status 会员状态
     * @return 会员列表
     */
    List<Member> findByStatus(Member.MemberStatus status);

    /**
     * 根据会员等级查找会员列表
     * @param level 会员等级
     * @return 会员列表
     */
    List<Member> findByLevel(Member.MemberLevel level);

    /**
     * 根据会员状态和等级查找会员列表
     * @param status 会员状态
     * @param level 会员等级
     * @return 会员列表
     */
    List<Member> findByStatusAndLevel(Member.MemberStatus status, Member.MemberLevel level);

    /**
     * 根据姓名模糊查询会员列表
     * @param name 会员姓名
     * @return 会员列表
     */
    @Query("SELECT m FROM Member m WHERE m.name LIKE %:name%")
    List<Member> findByNameContaining(@Param("name") String name);

    /**
     * 查找所有活跃会员
     * @return 活跃会员列表
     */
    @Query("SELECT m FROM Member m WHERE m.status = 'ACTIVE'")
    List<Member> findAllActiveMembers();

    /**
     * 统计各会员等级的会员数量
     * @return 会员等级统计结果
     */
    @Query("SELECT m.level, COUNT(m) FROM Member m GROUP BY m.level")
    List<Object[]> countMembersByLevel();

    /**
     * 统计各会员状态的会员数量
     * @return 会员状态统计结果
     */
    @Query("SELECT m.status, COUNT(m) FROM Member m GROUP BY m.status")
    List<Object[]> countMembersByStatus();
}